# 🔐 FIREBASE AUTHORIZED DOMAINS SETUP

## ⚠️ KRITISK: Tilføj disse domainer til Firebase Console

### 1. Åbn Firebase Console
🔗 **Direct link:** https://console.firebase.google.com/project/newagent-b33f9/authentication/settings

### 2. Gå til Authentication → Settings → Authorized Domains

Du SKAL tilføje disse domainer:

```
✅ localhost                                    (for lokal udvikling)
✅ mybestshape2day-lgtm.github.io              (GitHub Pages)
✅ trøstmig.dk                                  (hvis du har custom domain)
```

### 3. Hvis domainer mangler får du fejlen:
```
auth/unauthorized-domain: This domain is not authorized for OAuth operations
```

## 🔧 SÅDAN TILFØJER DU DOMAINER:

1. **Klik "Add domain"** 
2. **Indtast:** `mybestshape2day-lgtm.github.io`
3. **Klik "Add"**
4. **Gentag for** `localhost` (hvis ikke allerede der)

---

## 🧪 TEST EFTER DOMAIN SETUP:

Åbn din site og kør i console:
```javascript
// Test om domainer virker
await window.firebaseDebug.testAuth();
```

Hvis det returnerer `true` - så virker det! 🎉

## 🚨 HVAD HVIS DET STADIG FEJLER?

Hvis du stadig får fejl, tjek:

### A) API Key Restrictions (Google Cloud Console)
1. Gå til: https://console.cloud.google.com/apis/credentials?project=newagent-b33f9  
2. Find API key: `AIzaSyCXsc50f5PF8_g47S0Q7wyH36dmOtmLo8Y`
3. **Klik Edit** ✏️
4. **Application restrictions:** None ELLER HTTP referrers
5. Hvis HTTP referrers, tilføj:
   ```
   mybestshape2day-lgtm.github.io/*
   localhost/*
   ```

### B) API Restrictions
Sørg for at disse APIs er aktiveret:
```
✅ Firebase Authentication API
✅ Cloud Firestore API  
✅ Firebase Realtime Database API
✅ Identity and Access Management (IAM) API
```

---

## ✅ SUCCESS CHECKLIST

Når alt virker skal du se:
```
🔥 Initializing TrøstMig.dk Firebase...
Project: newagent-b33f9
App ID: 1:861717699185:web:9f1c1d8d8ce1be122f59d0
✅ Firebase initialized successfully!
✅ Firebase Analytics initialized
🔓 No user authenticated
🧪 Testing Firebase Authentication...
✅ Anonymous authentication successful: [UID]
✅ Firestore write test successful
✅ Realtime Database test successful
✅ Test completed - signed out
🔧 Firebase debug tools available: window.firebaseDebug
🎯 Ready for authentication and database operations!
```

**Hvis du ser det ovenfor = PROBLEM LØST!** 🚀