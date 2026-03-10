(() => {
    const { createApp, nextTick } = Vue;
    const root = document.getElementById('consultant');

    if (!root) {
        return;
    }

    const tokenUrl = root.dataset.tokenUrl || '/api/chat/token';

    createApp({
        delimiters: ['[[', ']]'],
        data() {
            return {
                isOpen: false,
                isTyping: false,
                hasOpened: false,
                unreadCount: 0,
                input: '',
                messages: [],
                quickReplies: [
                    'Нужна AI-стратегия продаж',
                    'Хотим автоматизировать поддержку',
                    'Интересует аудит данных',
                    'Оставить контакты',
                ],
                leadForm: {
                    name: '',
                    phone: '',
                    company: '',
                    comment: '',
                },
                leadSending: false,
                leadSent: false,
                leadTriedSubmit: false,
                showLeadForm: false,
                messageCounter: 0,
                nudgeTimer: null,
                ws: null,
                wsConnected: false,
                wsConnecting: false,
                wsConnectingPromise: null,
                wsQueue: [],
                pendingBotReplies: 0,
                pendingLocalMessages: [],
                historyLoaded: false,
                tokenUrl,
            };
        },
        computed: {
            leadPhoneDigits() {
                return (this.leadForm.phone || '').replace(/\D/g, '');
            },
            isLeadNameValid() {
                return !!(this.leadForm.name || '').trim();
            },
            isLeadPhoneValid() {
                return this.leadPhoneDigits.length === 11;
            },
            isLeadFormValid() {
                return this.isLeadNameValid && this.isLeadPhoneValid;
            },
            leadSubmitLabel() {
                if (this.leadSent) return 'Заявка отправлена';
                return this.leadSending ? 'Отправляем...' : 'Получить консультацию';
            },
        },
        methods: {
            toggleOpen() {
                this.isOpen = !this.isOpen;
                if (this.isOpen) {
                    this.handleOpen();
                }
            },
            handleOpen() {
                this.unreadCount = 0;
                if (!this.hasOpened) {
                    this.hasOpened = true;
                }
                this.scrollToBottom();
            },
            close() {
                this.isOpen = false;
            },
            formatPhone(raw) {
                let digits = (raw || '').replace(/\D/g, '');

                if (digits.startsWith('8')) digits = '7' + digits.slice(1);
                if (!digits.startsWith('7')) digits = '7' + digits;

                digits = digits.slice(0, 11);

                let res = '+7';
                if (digits.length > 1) res += ' (' + digits.slice(1, 4);
                if (digits.length >= 5) res += ') ' + digits.slice(4, 7);
                if (digits.length >= 8) res += '-' + digits.slice(7, 9);
                if (digits.length >= 10) res += '-' + digits.slice(9, 11);

                return res;
            },
            onLeadPhoneFocus() {
                if (!this.leadForm.phone) {
                    this.leadForm.phone = '+7';
                }
            },
            onLeadPhoneInput(e) {
                this.leadForm.phone = this.formatPhone(e.target.value);
            },
            getCsrfToken() {
                const name = 'csrftoken=';
                const decoded = decodeURIComponent(document.cookie || '');
                const parts = decoded.split(';');
                for (let i = 0; i < parts.length; i++) {
                    const item = parts[i].trim();
                    if (item.startsWith(name)) {
                        return item.substring(name.length);
                    }
                }
                return '';
            },
            async submitFormPayload(formType, payload) {
                const response = await fetch('/send_form', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken(),
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        form_type: formType,
                        payload,
                    }),
                });
                if (!response.ok) {
                    throw new Error('submit_failed');
                }
                return response.json();
            },
            createMessage(from, text) {
                this.messageCounter += 1;
                return {
                    id: this.messageCounter,
                    from,
                    text,
                    time: this.getTimeLabel(),
                };
            },
            getTimeLabel() {
                return new Date().toLocaleTimeString('ru-RU', {
                    hour: '2-digit',
                    minute: '2-digit',
                });
            },
            pushMessage(from, text, options = {}) {
                if (!text) return;
                this.messages.push(this.createMessage(from, text));
                if (!this.isOpen && !options.silent && from === 'bot') {
                    this.unreadCount += 1;
                }
                this.scrollToBottom();
            },
            scrollToBottom() {
                nextTick(() => {
                    const body = this.$refs.body;
                    if (!body) return;
                    body.scrollTop = body.scrollHeight;
                });
            },
            sendQuick(text) {
                this.sendMessage(text, { fromQuick: true });
            },
            sendMessage(text, options = {}) {
                const messageText = (typeof text === 'string' ? text : this.input).trim();
                if (!messageText) return;

                this.pushMessage('user', messageText);
                if (!this.historyLoaded) {
                    this.pendingLocalMessages.push(messageText);
                }
                if (!options.fromQuick) {
                    this.input = '';
                }
                if (this.quickReplies.length) {
                    this.quickReplies = [];
                }
                this.handleBotReply(messageText);
            },
            async handleBotReply(text) {
                const lower = text.toLowerCase();
                const wantsContact =
                    lower.includes('контакт') || lower.includes('заявк') || lower.includes('связ');
                if (wantsContact) {
                    this.showLeadForm = true;
                }
                this.isTyping = true;
                try {
                    await this.sendWsMessage(text);
                } catch (error) {
                    // eslint-disable-next-line no-console
                    console.error(error);
                    this.isTyping = false;
                    this.replyWithDelay('Сейчас не получается подключиться к консультанту. Попробуйте чуть позже.');
                }
            },
            async ensureSocket() {
                if (this.wsConnected) return;
                if (this.wsConnectingPromise) {
                    return this.wsConnectingPromise;
                }
                this.wsConnecting = true;
                this.wsConnectingPromise = (async () => {
                    const response = await fetch(this.tokenUrl, {
                        method: 'GET',
                        credentials: 'same-origin',
                    });
                    if (!response.ok) {
                        throw new Error('token_request_failed');
                    }
                    const data = await response.json();
                    const wsUrl = data.ws_url;
                    const token = data.token;
                    if (!wsUrl || !token) {
                        throw new Error('token_missing');
                    }
                    const url = wsUrl.includes('?')
                        ? `${wsUrl}&token=${encodeURIComponent(token)}`
                        : `${wsUrl}?token=${encodeURIComponent(token)}`;
                    await new Promise((resolve, reject) => {
                        const ws = new WebSocket(url);
                        this.ws = ws;
                        ws.onopen = () => {
                            this.wsConnected = true;
                            this.wsConnecting = false;
                            resolve();
                            this.flushWsQueue();
                        };
                        ws.onmessage = (event) => this.handleWsMessage(event);
                        ws.onerror = () => {
                            this.wsConnecting = false;
                            reject(new Error('ws_error'));
                        };
                        ws.onclose = () => {
                            this.wsConnected = false;
                            this.wsConnecting = false;
                            this.wsConnectingPromise = null;
                            this.ws = null;
                        };
                    });
                })();
                return this.wsConnectingPromise;
            },
            flushWsQueue() {
                while (this.wsConnected && this.wsQueue.length) {
                    const payload = this.wsQueue.shift();
                    this.ws.send(payload);
                }
            },
            restoreHistory(items) {
                const restored = [];
                let counter = 0;
                items.forEach(item => {
                    if (!item || typeof item.text !== 'string') return;
                    const text = item.text.trim();
                    if (!text) return;
                    const role = item.role === 'assistant' ? 'bot' : 'user';
                    counter += 1;
                    restored.push({
                        id: counter,
                        from: role,
                        text,
                        time: this.getTimeLabel(),
                    });
                });

                this.messages = restored;
                this.messageCounter = counter;
                this.unreadCount = 0;
                this.historyLoaded = true;

                if (this.pendingLocalMessages.length) {
                    this.pendingLocalMessages.forEach(text => {
                        const last = this.messages[this.messages.length - 1];
                        if (last && last.from === 'user' && last.text === text) {
                            return;
                        }
                        this.pushMessage('user', text, { silent: true });
                    });
                    this.pendingLocalMessages = [];
                }

                this.scrollToBottom();
            },
            handleWsMessage(event) {
                let reply = '';
                if (typeof event.data === 'string') {
                    try {
                        const parsed = JSON.parse(event.data);
                        if (parsed && parsed.type === 'history' && Array.isArray(parsed.messages)) {
                            this.restoreHistory(parsed.messages);
                            return;
                        }
                        if (parsed && typeof parsed.text === 'string') {
                            reply = parsed.text;
                        } else if (parsed && typeof parsed.message === 'string') {
                            reply = parsed.message;
                        } else if (typeof parsed === 'string') {
                            reply = parsed;
                        }
                    } catch (e) {
                        reply = event.data;
                    }
                }
                if (reply) {
                    this.pushMessage('bot', reply);
                }
                this.pendingBotReplies = Math.max(0, this.pendingBotReplies - 1);
                if (this.pendingBotReplies === 0) {
                    this.isTyping = false;
                }
            },
            async sendWsMessage(text) {
                await this.ensureSocket();
                const payload = JSON.stringify({ text });
                this.pendingBotReplies += 1;
                if (this.wsConnected && this.ws) {
                    this.ws.send(payload);
                } else {
                    this.wsQueue.push(payload);
                }
            },
            replyWithDelay(text) {
                this.isTyping = true;
                setTimeout(() => {
                    this.isTyping = false;
                    this.pushMessage('bot', text);
                }, 700 + Math.random() * 500);
            },
            async submitLead() {
                if (this.leadSending || this.leadSent) return;
                this.leadTriedSubmit = true;
                if (!this.isLeadFormValid) {
                    return;
                }
                this.leadSending = true;
                try {
                    await this.submitFormPayload('consultant_lead', {
                        ...this.leadForm,
                        message: this.leadForm.comment || '',
                        page: window.location.pathname,
                    });
                    this.leadSent = true;
                    this.pushMessage('bot', 'Спасибо! Мы получили заявку и свяжемся с вами в ближайшее рабочее время.');
                    this.showLeadForm = false;
                } catch (error) {
                    // eslint-disable-next-line no-console
                    console.error(error);
                } finally {
                    this.leadSending = false;
                }
            },
            scheduleNudge() {
                this.nudgeTimer = setTimeout(() => {
                    if (!this.isOpen && !this.hasOpened) {
                        this.pushMessage('bot', 'Могу быстро подсказать, где AI даст максимальный эффект. Напишите пару слов о вашей задаче.');
                    }
                }, 12000);
            },
        },
        mounted() {
            this.pushMessage('bot', 'Здравствуйте! Я онлайн-консультант BUYES AI. Чем могу помочь?', { silent: true });
            this.scheduleNudge();
        },
        beforeUnmount() {
            if (this.nudgeTimer) {
                clearTimeout(this.nudgeTimer);
            }
        },
    }).mount(root);
})();
