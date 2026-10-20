# 🔐 Firebase Firestore Security Rules (Strict Database-Driven Roles)

Use these rules in the Firebase Console. There are **NO hardcoded admin emails**; permissions are driven strictly by the `role` field in the user's document in the `users` collection in Firestore.

---

### Step 1: Open Firebase Console Rules
1. Open [Firebase Console](https://console.firebase.google.com/) & select **`zora-4b5eb`**.
2. Go to **Firestore Database** &rarr; **Rules** tab.

---

### Step 2: Copy & Paste These Rules

```javascript
rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {

    // Helper: Check if request is authenticated
    function isAuthenticated() {
      return request.auth != null;
    }

    // Helper: Check if user has 'admin' role in their Firestore user document
    function isAdmin() {
      return isAuthenticated() && 
        exists(/databases/$(database)/documents/users/$(request.auth.uid)) &&
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }

    // Users Collection (User Profiles & Roles)
    match /users/{userId} {
      allow read: if isAuthenticated();
      // Allow user to create their initial profile document during signup
      allow create: if isAuthenticated() && request.auth.uid == userId;
      // Only users who are already admin can change roles or modify user profiles
      allow update: if isAdmin();
      allow delete: if isAdmin();
    }

    // Licenses Collection (Hardware / Client Keys)
    match /licenses/{licenseKey} {
      allow read: if true;
      allow write: if isAdmin();
    }

    // Telemetry & Metrics Collection
    match /stats/{statDoc} {
      allow read: if true;
      allow write: if isAdmin();
    }
  }
}
```

---

### Step 3: How to make an account Admin manually
1. In Firebase Console &rarr; **Firestore Database** &rarr; **`users`** collection.
2. Click the document corresponding to the user's UID.
3. Edit the `role` field value from `user` to `admin` (or vice-versa).
4. As soon as you save, the live website automatically updates in real-time via the real-time snapshot listener!
