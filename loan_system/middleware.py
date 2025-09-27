from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class RequireAuthenticationMiddleware:
    """Enforce authentication for every request that is not explicitly exempt."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = resolve_url(getattr(settings, "LOGIN_URL", "/admin/login/"))
        self.public_exact, self.public_prefixes = self._build_whitelists()

    def __call__(self, request):
        if self._is_allowed(request):
            return self.get_response(request)

        if self._wants_json(request):
            return self._json_unauthorized()

        if request.method not in SAFE_METHODS:
            return self._html_blocked(request)

        return HttpResponseRedirect(self._login_redirect_url(request))

    # ------------------------------------------------------------------
    # Helper methods

    def _build_whitelists(self):
        exact = set()
        prefixes = set()

        def norm_prefix(value):
            if not value:
                return None
            value = "/" + value.lstrip("/")
            normalized = value if value.endswith("/") else f"{value}/"
            if normalized == "/":
                return None
            return normalized

        def norm_exact(value):
            if not value:
                return None
            normalized = "/" + value.lstrip("/")
            if normalized == "/":
                return None
            return normalized

        for item in getattr(settings, "LOGIN_EXEMPT_URLS", ()):  # exact matches
            normalized = norm_exact(item)
            if normalized:
                exact.add(normalized)

        for item in getattr(settings, "LOGIN_EXEMPT_PATH_PREFIXES", ()):  # prefixes
            normalized = norm_prefix(item)
            if normalized:
                prefixes.add(normalized)

        for attr in ("STATIC_URL", "MEDIA_URL"):
            normalized = norm_prefix(getattr(settings, attr, None))
            if normalized:
                prefixes.add(normalized)

        exact.add(norm_exact(self.login_url))
        exact.add("/favicon.ico")
        exact.add("/robots.txt")

        return tuple(sorted(exact)), tuple(sorted(prefixes))

    def _is_allowed(self, request):
        path = request.path
        user = getattr(request, "user", None)

        if user is not None and user.is_authenticated:
            return True

        if path in self.public_exact:
            return True

        for prefix in self.public_prefixes:
            if path.startswith(prefix):
                return True

        return False

    def _wants_json(self, request):
        accept = request.headers.get("Accept", "")
        if "application/json" in accept.lower():
            return True

        content_type = request.headers.get("Content-Type", "")
        if "application/json" in content_type.lower():
            return True

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return True

        return False

    def _login_redirect_url(self, request):
        next_url = request.get_full_path()
        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/"

        separator = "&" if "?" in self.login_url else "?"
        return f"{self.login_url}{separator}{urlencode({'next': next_url})}"

    @staticmethod
    def _json_unauthorized():
        response = JsonResponse(
            {"detail": "Authentication required.", "code": "not_authenticated"},
            status=401,
        )
        response["WWW-Authenticate"] = "Session"
        return response

    def _html_blocked(self, request):
        login_url = self._login_redirect_url(request)
        body = (
            "<h1>Authentication required</h1>"
            "<p>Your session has expired or you are not signed in.</p>"
            f'<p>Please <a href="{login_url}">log in</a> in another tab, then return and '
            "retry your action.</p>"
        )
        response = HttpResponse(body, status=403)
        response["WWW-Authenticate"] = "Session"
        return response
