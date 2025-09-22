// tracker.js - RETTET TIL TRØSTMIG.DK
// Håndterer både trøstmig.dk og xn--trstmig-rta.dk
// Nu med Firebase i stedet for PHP API

(function() {
    'use strict';
    
    // Firebase configuration
    const firebaseConfig = {
        apiKey: "AIzaSyBwN_aq90PzVsw7gwd33cxCGbNj-DAeifk",
        authDomain: "newagent-b33f9.firebaseapp.com",
        databaseURL: "https://newagent-b33f9.firebaseio.com/",
        projectId: "newagent-b33f9",
        storageBucket: "newagent-b33f9.firebasestorage.app",
        messagingSenderId: "861717699185",
        appId: "1:861717699185:web:9f1c1d8d8ce1be122f59d0"
    };

    // Initialize Firebase (check if already initialized)
    let app, database;
    try {
        app = firebase.app();
        database = firebase.database();
    } catch (e) {
        app = firebase.initializeApp(firebaseConfig);
        database = firebase.database();
    }

    console.log('TrøstMig Tracker - Using Firebase:', database);

    // Bruger ID
    let userId = localStorage.getItem('trostmig_userID');
    if (!userId) {
        userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('trostmig_userID', userId);
    }

    // Session tracking
    let currentSessionId = sessionStorage.getItem('trostmig_sessionId');

    // Send data til Firebase
    function sendToFirebase(action, data) {
        return database.ref('tracking/' + userId).push({
            action: action,
            data: data,
            timestamp: firebase.database.ServerValue.TIMESTAMP,
            sessionId: currentSessionId,
            userAgent: navigator.userAgent,
            url: window.location.href
        }).then(() => {
            console.log('✅ Bruger oprettet:', data);
            return { success: true };
        }).catch((error) => {
            console.error('❌ Firebase error:', error);
            return { success: false, error: error.message };
        });
    }

    function startSession(category) {
        const sessionData = {
            userId: userId,
            category: category,
            startTime: new Date().toISOString(),
            userAgent: navigator.userAgent
        };

        return database.ref('sessions/' + userId).push(sessionData)
            .then((ref) => {
                currentSessionId = ref.key;
                sessionStorage.setItem('trostmig_sessionId', currentSessionId);
                console.log('✅ Session startet:', sessionData);
                return { success: true, sessionId: currentSessionId };
            })
            .catch((error) => {
                console.error('❌ Session start error:', error);
                return { success: false, error: error.message };
            });
    }

    function endSession() {
        if (!currentSessionId) return Promise.resolve({ success: true });

        return database.ref('sessions/' + userId + '/' + currentSessionId).update({
            endTime: new Date().toISOString(),
            duration: Date.now() - sessionStorage.getItem('session_start_time')
        }).then(() => {
            sessionStorage.removeItem('trostmig_sessionId');
            console.log('✅ Session afsluttet');
            return { success: true };
        }).catch((error) => {
            console.error('❌ Session end error:', error);
            return { success: false, error: error.message };
        });
    }

    // Mood tracking
    function trackMood(mood) {
        const moodData = {
            mood: mood,
            date: new Date().toISOString().split('T')[0], // YYYY-MM-DD format
            timestamp: Date.now()
        };

        return sendToFirebase('mood_update', moodData);
    }

    // Activity tracking
    function trackActivity(activity, details = {}) {
        const activityData = {
            activity: activity,
            details: details,
            timestamp: Date.now()
        };

        return sendToFirebase('activity', activityData);
    }

    // Progress tracking
    function trackProgress(category, progress) {
        const progressData = {
            category: category,
            progress: progress,
            timestamp: Date.now()
        };

        return sendToFirebase('progress', progressData);
    }

    // Get user statistics
    function getUserStats() {
        return database.ref('tracking/' + userId).once('value')
            .then((snapshot) => {
                const data = snapshot.val();
                if (!data) return { totalSessions: 0, activeDays: 0, moodImprovement: 0 };

                // Calculate stats
                const activities = Object.values(data);
                const moodEntries = activities.filter(a => a.action === 'mood_update');
                const sessions = activities.filter(a => a.action === 'session_start');
                
                // Calculate active days
                const uniqueDays = new Set(activities.map(a => 
                    new Date(a.timestamp).toISOString().split('T')[0]
                ));

                // Calculate mood improvement
                let moodImprovement = 0;
                if (moodEntries.length >= 2) {
                    const firstMood = moodEntries[0].data.mood;
                    const lastMood = moodEntries[moodEntries.length - 1].data.mood;
                    moodImprovement = ((lastMood - firstMood) / firstMood) * 100;
                }

                return {
                    totalSessions: sessions.length,
                    activeDays: uniqueDays.size,
                    moodImprovement: Math.round(moodImprovement),
                    moodEntries: moodEntries.length
                };
            })
            .catch((error) => {
                console.error('Error getting stats:', error);
                return { totalSessions: 0, activeDays: 0, moodImprovement: 0 };
            });
    }

    // Global functions
    window.TrøstMigTracker = {
        sendToFirebase: sendToFirebase,
        startSession: startSession,
        endSession: endSession,
        trackMood: trackMood,
        trackActivity: trackActivity,
        trackProgress: trackProgress,
        getUserStats: getUserStats,
        userId: userId
    };

    // Auto-initialize
    console.log('TrøstMig Tracker initialized with Firebase');
    
    // Send initialization event
    sendToFirebase('tracker_init', {
        url: window.location.href,
        referrer: document.referrer,
        timestamp: Date.now()
    });

})();