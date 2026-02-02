const { createApp } = Vue;

createApp({
    // Options API
    delimiters: ['[[', ']]'],
    data() {
        return {
            name: '',
            phone: '',
            company: '',
            direction: 'Отдел продаж',
            isSending: false,
            sent: false,
            heroTriedSubmit: false,
            companySuggestions: [],
            isCompanySuggesting: false,
            companySuggestTimer: null,
            companySuggestAbort: null,
            companySuggestionsOpen: false,
            companyBlurTimer: null,
            quizForm: {
                industry: '',
                teamSize: '',
                department: '',
                pain: '',
                turnover: '',
            },
            isSendingQuiz: false,
            quizSent: false,
            quizTriedSubmit: false,
            isDiscussOpen: false,
            discussTopic: '',
            PlanForm: {
                name: '',
                phone: '',
                company: '',
                comment: '',
            },
            discussForm: {
                name: '',
                phone: '',
                company: '',
                comment: '',
            },
            discussCompanySuggestions: [],
            isDiscussCompanySuggesting: false,
            discussCompanySuggestTimer: null,
            discussCompanySuggestAbort: null,
            discussCompanySuggestionsOpen: false,
            discussCompanyBlurTimer: null,
            isSendingDiscuss: false,
            discussSent: false,

        };
    },
    computed: {
        heroPhoneDigits() {
            return (this.phone || '').replace(/\D/g, '');
        },
        isHeroNameValid() {
            return !!(this.name || '').trim();
        },
        isHeroPhoneValid() {
            return this.heroPhoneDigits.length === 11;
        },
        isHeroCompanyValid() {
            return !!(this.company || '').trim();
        },
        isHeroDirectionValid() {
            return !!(this.direction || '').trim();
        },
        isHeroFormValid() {
            return !!(this.isHeroNameValid && this.isHeroCompanyValid && this.isHeroDirectionValid && this.isHeroPhoneValid);
        },
        isQuizIndustryValid() {
            return !!(this.quizForm.industry || '').trim();
        },
        isQuizTeamSizeValid() {
            const teamSize = String(this.quizForm.teamSize || '').trim();
            const teamSizeNum = Number.parseInt(teamSize, 10);
            return !!(teamSize && Number.isFinite(teamSizeNum) && teamSizeNum > 0);
        },
        isQuizDepartmentValid() {
            return !!(this.quizForm.department || '').trim();
        },
        isQuizPainValid() {
            return !!(this.quizForm.pain || '').trim();
        },
        isQuizFormValid() {
            return !!(this.isQuizIndustryValid && this.isQuizTeamSizeValid && this.isQuizDepartmentValid && this.isQuizPainValid);
        },
    },
    methods: {
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
        
          // универсальный геттер/сеттер по строковому пути типа "discussForm.phone"
          getByPath(path) {
            return path.split('.').reduce((obj, key) => obj && obj[key], this);
          },
          setByPath(path, value) {
            const parts = path.split('.');
            let obj = this;
            for (let i = 0; i < parts.length - 1; i++) {
              obj = obj[parts[i]];
            }
            obj[parts[parts.length - 1]] = value;
          },
        
          onPhoneFocus(path) {
            const current = this.getByPath(path);
            if (!current) {
              this.setByPath(path, '+7');
            }
          },
        
          onPhoneInput(path, e) {
            const formatted = this.formatPhone(e.target.value);
            this.setByPath(path, formatted);
          },

          onCompanyInput(e) {
            const query = (e && e.target && e.target.value) ? e.target.value : this.company;
            this.companySuggestionsOpen = true;
            this.fetchCompanySuggestions(query);
          },

          onCompanyFocus() {
            if (this.companySuggestions.length > 0) {
                this.companySuggestionsOpen = true;
            }
          },

          onCompanyBlur() {
            if (this.companyBlurTimer) {
                clearTimeout(this.companyBlurTimer);
            }
            this.companyBlurTimer = setTimeout(() => {
                this.companySuggestionsOpen = false;
            }, 150);
          },

          selectCompanySuggestion(item) {
            if (!item) return;
            this.company = item.value || '';
            this.companySuggestionsOpen = false;
            this.companySuggestions = [];
          },

          fetchCompanySuggestions(query) {
            const value = (query || '').trim();
            if (this.companySuggestTimer) {
                clearTimeout(this.companySuggestTimer);
            }
            if (value.length < 2) {
                this.companySuggestions = [];
                this.companySuggestionsOpen = false;
                return;
            }
            this.companySuggestTimer = setTimeout(() => {
                this.requestCompanySuggestions(value);
            }, 250);
          },

          async requestCompanySuggestions(query) {
            if (this.companySuggestAbort) {
                this.companySuggestAbort.abort();
            }
            const controller = new AbortController();
            this.companySuggestAbort = controller;
            this.isCompanySuggesting = true;
            try {
                const resp = await fetch(`/api/dadata/party/?q=${encodeURIComponent(query)}`, {
                    signal: controller.signal,
                });
                if (!resp.ok) {
                    this.companySuggestions = [];
                    return;
                }
                const data = await resp.json();
                this.companySuggestions = Array.isArray(data.suggestions) ? data.suggestions : [];
                this.companySuggestionsOpen = this.companySuggestions.length > 0;
            } catch (e) {
                if (e && e.name !== 'AbortError') {
                    this.companySuggestions = [];
                }
            } finally {
                this.isCompanySuggesting = false;
            }
          },

          onDiscussCompanyInput(e) {
            const query = (e && e.target && e.target.value) ? e.target.value : this.discussForm.company;
            this.discussCompanySuggestionsOpen = true;
            this.fetchDiscussCompanySuggestions(query);
          },

          onDiscussCompanyFocus() {
            if (this.discussCompanySuggestions.length > 0) {
                this.discussCompanySuggestionsOpen = true;
            }
          },

          onDiscussCompanyBlur() {
            if (this.discussCompanyBlurTimer) {
                clearTimeout(this.discussCompanyBlurTimer);
            }
            this.discussCompanyBlurTimer = setTimeout(() => {
                this.discussCompanySuggestionsOpen = false;
            }, 150);
          },

          selectDiscussCompanySuggestion(item) {
            if (!item) return;
            this.discussForm.company = item.value || '';
            this.discussCompanySuggestionsOpen = false;
            this.discussCompanySuggestions = [];
          },

          fetchDiscussCompanySuggestions(query) {
            const value = (query || '').trim();
            if (this.discussCompanySuggestTimer) {
                clearTimeout(this.discussCompanySuggestTimer);
            }
            if (value.length < 2) {
                this.discussCompanySuggestions = [];
                this.discussCompanySuggestionsOpen = false;
                return;
            }
            this.discussCompanySuggestTimer = setTimeout(() => {
                this.requestDiscussCompanySuggestions(value);
            }, 250);
          },

          async requestDiscussCompanySuggestions(query) {
            if (this.discussCompanySuggestAbort) {
                this.discussCompanySuggestAbort.abort();
            }
            const controller = new AbortController();
            this.discussCompanySuggestAbort = controller;
            this.isDiscussCompanySuggesting = true;
            try {
                const resp = await fetch(`/api/dadata/party/?q=${encodeURIComponent(query)}`, {
                    signal: controller.signal,
                });
                if (!resp.ok) {
                    this.discussCompanySuggestions = [];
                    return;
                }
                const data = await resp.json();
                this.discussCompanySuggestions = Array.isArray(data.suggestions) ? data.suggestions : [];
                this.discussCompanySuggestionsOpen = this.discussCompanySuggestions.length > 0;
            } catch (e) {
                if (e && e.name !== 'AbortError') {
                    this.discussCompanySuggestions = [];
                }
            } finally {
                this.isDiscussCompanySuggesting = false;
            }
          },
    
        
        async submitHeroForm() {
            if (this.isSending || this.sent) return;
            this.heroTriedSubmit = true;
            if (!this.isHeroFormValid) {
                return;
            }
            const name = this.name.trim();
            const phone = this.phone.trim();
            const company = this.company.trim();
            const direction = (this.direction || '').trim();
            this.isSending = true;
            try {
                // здесь будет реальный POST на Django
                console.log('Отправка:', {
                    name,
                    phone,
                    company,
                    direction,
                });
                // имитация задержки
                await new Promise(r => setTimeout(r, 1000));
                this.sent = true;
            } finally {
                this.isSending = false;
            }
        },
        async submitQuiz() {
            if (this.isSendingQuiz || this.quizSent) return;
            this.quizTriedSubmit = true;
            if (!this.isQuizFormValid) {
                return;
            }
            this.isSendingQuiz = true;
            try {
                console.log('Quiz form payload:', {
                    ...this.quizForm,
                });
                await new Promise(r => setTimeout(r, 1000));
                this.quizSent = true;
            } finally {
                this.isSendingQuiz = false;
            }
        },
        openDiscuss(topic) {
            this.discussTopic = topic || '';
            this.isDiscussOpen = true;
            this.discussSent = false;
            this.isSendingDiscuss = false;
        },
        closeDiscuss() {
            this.isDiscussOpen = false;
        },

        async submitDiscuss() {
            if (this.isSendingDiscuss) return;
            this.isSendingDiscuss = true;
            try {
                // TODO: здесь реальный POST на backend (Django view / API)
                // Пример:
                // await fetch('{% url "lead_discuss" %}', {
                //   method: 'POST',
                //   headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
                //   body: JSON.stringify({ ...this.discussForm, topic: this.discussTopic }),
                // });

                console.log('Discuss form payload:', {
                    ...this.discussForm,
                    topic: this.discussTopic,
                });

                await new Promise(r => setTimeout(r, 500)); // имитация задержки
                this.discussSent = true;
                // Если надо чистить поля:
                this.discussForm = { name: '', phone: '', company: '', comment: '' };
            } catch (e) {
                console.error(e);
            } finally {
                this.isSendingDiscuss = false;
                this.closeDiscuss()
            }
        },
    }
}).mount('#app');   // ← важный момент: элемент с id="app"

// скрываем прелоадер, когда вся страница загрузилась
window.addEventListener('load', () => {
    const preloader = document.getElementById('preloader');
    if (!preloader) return;

    preloader.classList.add('preloader-hide');
    // полностью убираем из DOM после анимации
    setTimeout(() => {
        if (preloader && preloader.parentNode) {
            preloader.parentNode.removeChild(preloader);
        }
    }, 400); // время = transition в CSS
});
