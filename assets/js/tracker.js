(function () {
    var STORAGE_KEY = 'buyes_tracking_state';
    var SESSION_URL = '/api/site-tracking/session/';
    var EVENT_URL = '/api/site-tracking/event/';
    var METRIKA_COUNTER_ID = 106808297;
    var ONCE_EVENTS = {
        page_view: true,
        chat_opened: true,
        first_message_sent: true,
    };

    function getCsrfToken() {
        var name = 'csrftoken=';
        var decoded = decodeURIComponent(document.cookie || '');
        var parts = decoded.split(';');
        for (var i = 0; i < parts.length; i += 1) {
            var item = parts[i].trim();
            if (item.indexOf(name) === 0) {
                return item.substring(name.length);
            }
        }
        return '';
    }

    function readState() {
        try {
            var raw = window.localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return {};
            }
            var parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (error) {
            return {};
        }
    }

    function writeState(state) {
        try {
            window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state || {}));
        } catch (error) {
            // ignore storage failures
        }
    }

    function generateSessionId() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') {
            return window.crypto.randomUUID();
        }
        return 'sess-' + Date.now() + '-' + Math.floor(Math.random() * 1000000);
    }

    function getState() {
        var state = readState();
        if (!state.session_id) {
            state.session_id = generateSessionId();
        }
        return state;
    }

    function normalizeText(value) {
        return String(value || '').trim();
    }

    function getUrlParams() {
        return new URLSearchParams(window.location.search || '');
    }

    function getUtmData() {
        var params = getUrlParams();
        var result = {};
        ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(function (key) {
            var value = normalizeText(params.get(key));
            if (value) {
                result[key] = value;
            }
        });
        return result;
    }

    function getYclid() {
        return normalizeText(getUrlParams().get('yclid'));
    }

    function getBasePayload() {
        var state = getState();
        var utmData = getUtmData();
        var payload = {
            session_id: state.session_id,
            referer: normalizeText(document.referrer),
            landing_url: normalizeText(state.landing_url || window.location.href),
            page_url: normalizeText(window.location.href),
            yclid: normalizeText(state.yclid || getYclid()),
            client_id: normalizeText(state.client_id),
        };
        Object.keys(utmData).forEach(function (key) {
            payload[key] = utmData[key];
        });
        return payload;
    }

    function saveBaseStateFromPayload(payload) {
        var state = getState();
        state.landing_url = state.landing_url || normalizeText(payload.landing_url);
        state.yclid = state.yclid || normalizeText(payload.yclid);
        if (payload.client_id) {
            state.client_id = normalizeText(payload.client_id);
        }
        writeState(state);
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify(payload),
        }).then(function (response) {
            if (!response.ok) {
                throw new Error('tracking_request_failed');
            }
            return response.json();
        });
    }

    function requestMetrikaClientId() {
        return new Promise(function (resolve) {
            if (typeof window.ym !== 'function') {
                resolve('');
                return;
            }

            var resolved = false;
            var timeoutId = window.setTimeout(function () {
                if (!resolved) {
                    resolved = true;
                    resolve('');
                }
            }, 1500);

            try {
                window.ym(METRIKA_COUNTER_ID, 'getClientID', function (clientId) {
                    if (resolved) {
                        return;
                    }
                    resolved = true;
                    window.clearTimeout(timeoutId);
                    resolve(normalizeText(clientId));
                });
            } catch (error) {
                if (!resolved) {
                    resolved = true;
                    window.clearTimeout(timeoutId);
                    resolve('');
                }
            }
        });
    }

    function markEventSent(eventType) {
        var state = getState();
        state.sent_events = state.sent_events || {};
        state.sent_events[eventType] = true;
        writeState(state);
    }

    function wasEventSent(eventType) {
        var state = getState();
        return !!(state.sent_events && state.sent_events[eventType]);
    }

    var initPromise = null;

    function initTracking() {
        if (initPromise) {
            return initPromise;
        }

        initPromise = (async function () {
            var payload = getBasePayload();
            saveBaseStateFromPayload(payload);
            await postJson(SESSION_URL, payload);
            markEventSent('page_view');

            var clientId = await requestMetrikaClientId();
            if (clientId) {
                var updatedPayload = getBasePayload();
                updatedPayload.client_id = clientId;
                saveBaseStateFromPayload(updatedPayload);
                await postJson(SESSION_URL, updatedPayload);
            }

            return getState();
        })().catch(function () {
            return getState();
        });

        return initPromise;
    }

    async function trackEvent(eventType, extraPayload) {
        if (!eventType) {
            return;
        }
        if (ONCE_EVENTS[eventType] && wasEventSent(eventType)) {
            return;
        }

        await initTracking();
        var payload = getBasePayload();
        payload.event_type = eventType;
        extraPayload = extraPayload && typeof extraPayload === 'object' ? extraPayload : {};
        Object.keys(extraPayload).forEach(function (key) {
            payload[key] = extraPayload[key];
        });
        await postJson(EVENT_URL, payload);
        if (ONCE_EVENTS[eventType]) {
            markEventSent(eventType);
        }
    }

    async function enrichPayload(payload) {
        await initTracking();
        payload = payload && typeof payload === 'object' ? payload : {};
        var state = getState();
        var utmData = getUtmData();
        var enriched = Object.assign({}, payload, {
            session_id: state.session_id,
            tracking_session_id: state.session_id,
            referer: payload.referer || document.referrer || '',
            landing_url: payload.landing_url || state.landing_url || window.location.href,
            client_id: payload.client_id || state.client_id || '',
            yclid: payload.yclid || state.yclid || getYclid() || '',
        });
        enriched.utm_data = Object.assign({}, utmData, payload.utm_data || {});
        return enriched;
    }

    function handleDocumentClick(event) {
        var target = event.target;
        if (!target || !target.closest) {
            return;
        }

        var link = target.closest('a[href]');
        if (!link) {
            return;
        }

        var href = normalizeText(link.getAttribute('href'));
        if (!href) {
            return;
        }

        if (href.indexOf('tel:') === 0) {
            trackEvent('phone_clicked', { href: href, label: normalizeText(link.textContent) }).catch(function () {});
            return;
        }

        var messengerPrefixes = [
            'https://t.me/',
            'http://t.me/',
            'https://wa.me/',
            'https://api.whatsapp.com/',
            'tg://',
            'whatsapp://',
            'viber://',
        ];
        for (var i = 0; i < messengerPrefixes.length; i += 1) {
            if (href.indexOf(messengerPrefixes[i]) === 0) {
                trackEvent('messenger_clicked', { href: href, label: normalizeText(link.textContent) }).catch(function () {});
                return;
            }
        }
    }

    document.addEventListener('click', handleDocumentClick, true);
    initTracking();

    window.BuyesTracker = {
        init: initTracking,
        trackEvent: trackEvent,
        enrichPayload: enrichPayload,
        getSessionId: function () {
            return getState().session_id || '';
        },
    };
})();
