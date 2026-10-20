# 🔐 Firebase Firestore Security Rules (Strict Database-Driven Roles & Heartbeats)

Use these rules in the Firebase Console. Permissions are strictly driven by the `role` field in the user's document in the `users` collection, with support for live daemon heartbeats.

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

    // Helper: Check if user has 'admin' role in Firestore database document
    function isAdmin() {
      return isAuthenticated() && 
        exists(/databases/$(database)/documents/users/$(request.auth.uid)) &&
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }

    // Users Collection (User Profiles & Roles)
    match /users/{userId} {
      allow read: if isAuthenticated();
      allow create: if isAuthenticated() && request.auth.uid == userId;
      allow update: if isAdmin();
      allow delete: if isAdmin();
    }

    // Licenses Collection (Hardware / Client Keys)
    match /licenses/{licenseKey} {
      allow read: if true;
      allow write: if isAdmin();
      // Allow live client daemons to report in_use and last_seen heartbeats
      allow update: if request.resource.data.diff(resource.data).affectedKeys().hasOnly(['in_use', 'last_seen']);
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
4. As soon as you save, the live website automatically updates in real-time!
