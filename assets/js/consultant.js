(() => {
    const { createApp, nextTick } = Vue;
    const root = document.getElementById('consultant');

    if (!root) {
        return;
    }

    const getCookie = (name) => {
        if (!document.cookie) return '';
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [key, ...valueParts] = cookie.trim().split('=');
            if (key === name) {
                return decodeURIComponent(valueParts.join('='));
            }
        }
        return '';
    };

    const apiUrl = root.dataset.apiUrl || '/api/consultant/chat/';

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
                apiUrl,
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
                    const reply = await this.fetchBotReply(text);
                    this.isTyping = false;
                    if (reply) {
                        this.pushMessage('bot', reply);
                        return;
                    }
                } catch (error) {
                    // eslint-disable-next-line no-console
                    console.error(error);
                    this.isTyping = false;
                }

                if (wantsContact) {
                    this.replyWithDelay('Оставьте контакты — я передам менеджеру, и мы предложим 1–2 сценария внедрения.');
                    return;
                }

                if (lower.includes('цена') || lower.includes('стоим') || lower.includes('бюджет')) {
                    this.replyWithDelay('Стоимость зависит от объёма данных и сценария. Обычно начинаем с пилота на 2–4 недели и фиксируем ROI. Что именно хотите автоматизировать?');
                    return;
                }

                if (lower.includes('поддерж') || lower.includes('чат')) {
                    this.replyWithDelay('Для поддержки часто внедряем AI-оператора: разгружает до 60% обращений и поднимает SLA. Можете описать текущий объём обращений?');
                    return;
                }

                if (lower.includes('продаж') || lower.includes('лид')) {
                    this.replyWithDelay('В продажах обычно даём скоринг лидов, рекомендации по следующему шагу и автоматизацию рутины. Какие каналы сейчас ключевые?');
                    return;
                }

                if (lower.includes('аудит') || lower.includes('данн')) {
                    this.replyWithDelay('Аудит занимает 3–5 рабочих дней: смотрим источники данных, качество и гипотезы по эффекту. Хотите, пришлю чек-лист подготовки?');
                    return;
                }

                this.replyWithDelay('Спасибо за вопрос! Чтобы подсказать точнее, расскажите, какой процесс хотите улучшить и сколько людей вовлечено.');
            },
            buildHistory() {
                const historySource = this.messages.slice(0, -1).slice(-12);
                return historySource
                    .filter(item => item && item.text)
                    .map(item => ({
                        role: item.from === 'bot' ? 'assistant' : 'user',
                        content: item.text,
                    }));
            },
            async fetchBotReply(text) {
                const csrfToken = getCookie('csrftoken');
                const response = await fetch(this.apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        message: text,
                        history: this.buildHistory(),
                    }),
                });

                if (!response.ok) {
                    let errorCode = '';
                    try {
                        const data = await response.json();
                        errorCode = data.error || '';
                    } catch (e) {
                        errorCode = '';
                    }
                    throw new Error(errorCode || 'Consultant API error');
                }

                const data = await response.json();
                return (data.reply || '').trim();
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
                    await new Promise(resolve => setTimeout(resolve, 900));
                    this.leadSent = true;
                    this.pushMessage('bot', 'Спасибо! Мы получили заявку и свяжемся с вами в ближайшее рабочее время.');
                    this.showLeadForm = false;
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
