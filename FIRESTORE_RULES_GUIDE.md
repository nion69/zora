# 🔐 How to Update Firebase Firestore Rules for Zora AI

To enable authentication, license creation, and role-based admin access, follow these quick steps:

---

### Step 1: Open Firebase Console
1. Go to **[https://console.firebase.google.com/](https://console.firebase.google.com/)**
2. Select your project: **`zora-4b5eb`**

---

### Step 2: Open Firestore Database Rules
1. In the left navigation menu, click on **Build** &rarr; **Firestore Database**
2. Click on the **Rules** tab at the top (next to *Data* and *Indexes*)

---

### Step 3: Paste the Updated Rules
Delete whatever is in the editor and paste the following:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Helper functions
    function isAuthenticated() {
      return request.auth != null;
    }

    function isAdmin() {
      return isAuthenticated() && (
        request.auth.token.email == "neon@zora.ai" ||
        request.auth.token.email == "sir76@gmail.com" ||
        request.auth.token.email.matches(".*neon.*") ||
        (exists(/databases/$(database)/documents/users/$(request.auth.uid)) &&
         get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == "admin")
      );
    }

    // 1. Licenses collection (Public read for terminal verification + stats, Write for authenticated users/admins)
    match /licenses/{keyId} {
      allow read: if true;
      allow write: if isAuthenticated();
    }

    // 2. Users collection (Auth & Role-Based Access Control)
    match /users/{userId} {
      allow read: if true;
      allow create: if isAuthenticated();
      allow update: if isAuthenticated();
      allow delete: if isAdmin();
    }

    // 3. Fallback for any other collections
    match /{document=**} {
      allow read: if true;
      allow write: if isAuthenticated();
    }
  }
}
```

---

### Step 4: Click Publish
Click the blue **Publish** button at the top right of the Rules editor.
Your new security rules take effect immediately across all web dashboards and terminals!

---

### Optional: 100% Open Development Mode
If you prefer zero restrictions during local testing:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
```
