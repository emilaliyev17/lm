# 🔧 Search Troubleshooting Guide

## ✅ Status Check

**Migration Applied:** ✅ YES (0014_add_invoice_search_indexes)  
**Server Running:** ✅ YES (restarted with new code)  
**Search Box Added:** ✅ YES (in loan_list.html)  

## 🧪 How to Test the Search

### Step 1: Open the Dashboard
1. Open your browser
2. Go to: **http://localhost:8000/api/loans/**
3. Make sure you're logged in

### Step 2: Find the Search Box
Look for a search input at the top of the page with placeholder text:
```
"Search by card number, borrower, or invoice number..."
```

### Step 3: Try Searching
Type any of these:
- **Card number**: "LC" or "LC-001"
- **Borrower name**: (any borrower name in your system)
- **Invoice number**: "SD" or any invoice number you have

### Step 4: Expected Behavior
- After typing 2+ characters, wait 300ms
- "Searching..." appears briefly
- Dropdown appears below search box
- Results show with colored badges and icons
- Click any result to go to that loan

## 🐛 Common Issues & Fixes

### Issue 1: "Search box doesn't appear"
**Cause:** Browser cache  
**Fix:**
1. Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
2. Or clear browser cache
3. Refresh the page

### Issue 2: "Nothing happens when I type"
**Check:**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for JavaScript errors (red text)
4. Screenshot and share any errors you see

**Common fix:**
- Make sure you're typing at least 2 characters
- Wait 300ms (stops typing for a moment)

### Issue 3: "Getting 404 error in console"
**Error:** `GET http://localhost:8000/api/loans/search/?q=test 404`

**Fix:** Server might need restart (already done above, but if still happening):
```bash
cd "/Users/emil.aliyev/My Projects/LM/loan-management-system"
source venv/bin/activate
pkill -f "manage.py runserver"
python manage.py runserver
```

### Issue 4: "Getting 403 or redirect to login"
**Cause:** Not logged in  
**Fix:**
1. Go to http://localhost:8000/admin/
2. Log in with your admin credentials
3. Then go back to http://localhost:8000/api/loans/

### Issue 5: "Search returns no results but data exists"
**Debug steps:**

1. Test the API directly in browser:
   - Go to: http://localhost:8000/api/loans/search/?q=LC
   - Should return JSON with results

2. Check if you have data:
   ```bash
   cd "/Users/emil.aliyev/My Projects/LM/loan-management-system"
   source venv/bin/activate
   python manage.py shell
   ```
   
   Then in the shell:
   ```python
   from loans.models import LoanCard
   print(LoanCard.objects.count())  # Should show number of loans
   print(LoanCard.objects.first().card_number)  # Show first card number
   ```

3. Try searching for that exact card number

## 🔍 Testing with Browser DevTools

### Open DevTools (F12), then:

1. **Console Tab** - Check for errors
   - Red text = JavaScript errors
   - Screenshot if you see any

2. **Network Tab** - Check API calls
   - Type in search box
   - Look for request to `/api/loans/search/?q=...`
   - Click on it
   - Check Status Code:
     - **200 OK** = Working! ✅
     - **404 Not Found** = URL issue ❌
     - **403 Forbidden** = Not logged in ❌
     - **500 Server Error** = Backend issue ❌

3. **Response** - Check what API returns
   - Click the search request in Network tab
   - Go to Response tab
   - Should see JSON with "results" array

## 📸 What to Check (Screenshot These)

If still not working, screenshot:
1. The page showing search box (or where it should be)
2. Browser Console tab (F12 → Console)
3. Browser Network tab (F12 → Network) while typing in search
4. The response from `/api/loans/search/` request

## 🎯 Quick Verification Script

Run this to verify search endpoint exists:

```bash
cd "/Users/emil.aliyev/My Projects/LM/loan-management-system"
source venv/bin/activate
python manage.py shell
```

Then paste:
```python
from django.urls import reverse
try:
    url = reverse('search_loans')
    print(f"✅ Search URL exists: {url}")
except:
    print("❌ Search URL not found - check urls.py")

from loans.views import search_loans
print(f"✅ Search view exists: {search_loans}")

from loans.models import LoanCard
count = LoanCard.objects.count()
print(f"✅ Loans in database: {count}")

if count > 0:
    first = LoanCard.objects.first()
    print(f"✅ Sample card number: {first.card_number}")
    print(f"✅ Sample borrower: {first.borrower.name}")
```

This should print all checkmarks ✅ if everything is set up correctly.

## 🆘 Still Not Working?

If you've tried all above and it's still not working, provide:
1. Screenshot of the page
2. Screenshot of Console (F12)
3. Screenshot of Network tab (F12) showing the search request
4. Output of the verification script above

## 📞 What to Report

When reporting issues, include:
- Browser name and version (Chrome, Firefox, Safari?)
- What you searched for
- What happened (or didn't happen)
- Any error messages from Console
- Screenshots

---

**Server is running on:** http://localhost:8000  
**Search endpoint:** http://localhost:8000/api/loans/search/  
**Migration status:** Applied ✅

