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
            isCompanySuggestionInteracting: false,
            selectedCompanyData: null,
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
            isSendingPlan: false,
            planSent: false,
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
            isDiscussCompanySuggestionInteracting: false,
            selectedDiscussCompanyData: null,
            isSendingDiscuss: false,
            discussSent: false,
            outsideClickHandler: null,

        };
    },
    mounted() {
        this.outsideClickHandler = (event) => {
            this.handleOutsideClick(event);
        };
        document.addEventListener('click', this.outsideClickHandler);
    },
    beforeUnmount() {
        if (this.outsideClickHandler) {
            document.removeEventListener('click', this.outsideClickHandler);
        }
        if (this.companySuggestTimer) {
            clearTimeout(this.companySuggestTimer);
        }
        if (this.companyBlurTimer) {
            clearTimeout(this.companyBlurTimer);
        }
        if (this.discussCompanySuggestTimer) {
            clearTimeout(this.discussCompanySuggestTimer);
        }
        if (this.discussCompanyBlurTimer) {
            clearTimeout(this.discussCompanyBlurTimer);
        }
        if (this.companySuggestAbort) {
            this.companySuggestAbort.abort();
        }
        if (this.discussCompanySuggestAbort) {
            this.discussCompanySuggestAbort.abort();
        }
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
        heroSubmitLabel() {
            if (this.sent) return 'Отправлено';
            return this.isSending ? 'Отправляем...' : 'Получить AI-стратегию';
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
        quizSubmitLabel() {
            if (this.quizSent) return 'Отправлено';
            return this.isSendingQuiz ? 'Отправляем...' : 'Получить расчёт и дорожную карту';
        },
        discussModalTitle() {
            return this.discussTopic || 'Внедрение AI под вашу задачу';
        },
        discussSubmitLabel() {
            return this.isSendingDiscuss ? 'Отправляем...' : 'Обсудить проект';
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

          getUtmData() {
            const params = new URLSearchParams(window.location.search || '');
            const utmData = {};
            for (const [key, value] of params.entries()) {
                if (!key.startsWith('utm_')) continue;
                const normalizedValue = (value || '').trim();
                if (!normalizedValue) continue;
                utmData[key] = normalizedValue;
            }
            return utmData;
          },

          async submitFormPayload(formType, payload) {
            const enrichedPayload = {
                ...payload,
                page_url: payload && payload.page_url ? payload.page_url : window.location.href,
            };
            if (!enrichedPayload.utm_data) {
                enrichedPayload.utm_data = this.getUtmData();
            }
            const response = await fetch('/send_form', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    form_type: formType,
                    payload: enrichedPayload,
                }),
            });
            if (!response.ok) {
                let details = '';
                try {
                    const err = await response.json();
                    details = err && err.error ? `: ${err.error}` : '';
                } catch (_) {
                    details = '';
                }
                throw new Error(`submit_failed${details}`);
            }
            return response.json();
          },

          normalizeSelectedCompanyData(item, fallbackName = '') {
            if (!item || typeof item !== 'object') {
              return fallbackName ? { name: fallbackName } : null;
            }
            const name = String(item.name || item.value || fallbackName || '').trim();
            const inn = String(item.inn || '').trim();
            const kpp = String(item.kpp || '').trim();
            const ogrn = String(item.ogrn || '').trim();
            const address = String(item.address || '').trim();
            const industry = String(item.industry || '').trim();
            const okved = String(item.okved || '').trim();
            const legalName = String(item.legal_name || '').trim();
            const normalized = { name };
            if (inn) normalized.inn = inn;
            if (kpp) normalized.kpp = kpp;
            if (ogrn) normalized.ogrn = ogrn;
            if (address) normalized.address = address;
            if (industry) normalized.industry = industry;
            if (okved) normalized.okved = okved;
            if (legalName) normalized.legal_name = legalName;
            if (Array.isArray(item.okveds) && item.okveds.length) normalized.okveds = item.okveds;
            if (item.director && typeof item.director === 'object') normalized.director = item.director;
            return normalized;
          },

          buildCompanyPayload(companyName, selectedCompanyData) {
            const normalizedName = String(companyName || '').trim();
            const selected = this.normalizeSelectedCompanyData(selectedCompanyData, normalizedName);
            if (!selected || !selected.name) {
              return {};
            }
            return {
              company_data: selected,
              company_name: selected.name,
              company_inn: selected.inn || '',
              company_kpp: selected.kpp || '',
              company_ogrn: selected.ogrn || '',
              company_address: selected.address || '',
              company_industry: selected.industry || '',
              company_okved: selected.okved || '',
              company_legal_name: selected.legal_name || '',
            };
          },

          async enrichCompanySelection(selectedCompanyData) {
            const normalized = this.normalizeSelectedCompanyData(selectedCompanyData);
            if (!normalized || !normalized.inn) {
              return normalized;
            }
            try {
              const response = await fetch(`/api/dadata/party/by-inn/?inn=${encodeURIComponent(normalized.inn)}`, {
                credentials: 'same-origin',
              });
              if (!response.ok) {
                return normalized;
              }
              const data = await response.json();
              if (!data || !data.profile || typeof data.profile !== 'object') {
                return normalized;
              }
              return {
                ...normalized,
                ...this.normalizeSelectedCompanyData(data.profile, normalized.name),
                okveds: Array.isArray(data.profile.okveds) ? data.profile.okveds : normalized.okveds,
                director: data.profile.director && typeof data.profile.director === 'object'
                  ? data.profile.director
                  : normalized.director,
              };
            } catch (_) {
              return normalized;
            }
          },

          onCompanyInput(e) {
            const query = (e && e.target && e.target.value) ? e.target.value : this.company;
            if (
              this.selectedCompanyData &&
              String(this.selectedCompanyData.name || '').trim() &&
              String(query || '').trim() !== String(this.selectedCompanyData.name || '').trim()
            ) {
              this.selectedCompanyData = null;
            }
            this.companySuggestionsOpen = true;
            this.fetchCompanySuggestions(query);
          },

          onCompanyFocus() {
            if (this.companyBlurTimer) {
                clearTimeout(this.companyBlurTimer);
            }
            if (this.companySuggestions.length > 0) {
                this.companySuggestionsOpen = true;
            }
          },

          onCompanyBlur() {
            if (this.companyBlurTimer) {
                clearTimeout(this.companyBlurTimer);
            }
            if (this.isCompanySuggestionInteracting) {
                this.isCompanySuggestionInteracting = false;
                return;
            }
            this.companyBlurTimer = setTimeout(() => {
                this.companySuggestionsOpen = false;
            }, 180);
          },

          startCompanySuggestionInteraction() {
            if (this.companyBlurTimer) {
                clearTimeout(this.companyBlurTimer);
            }
            this.isCompanySuggestionInteracting = true;
          },

          async selectCompanySuggestion(item) {
            if (!item) return;
            this.isCompanySuggestionInteracting = false;
            this.company = item.value || '';
            this.selectedCompanyData = await this.enrichCompanySelection(item);
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
            if (
              this.selectedDiscussCompanyData &&
              String(this.selectedDiscussCompanyData.name || '').trim() &&
              String(query || '').trim() !== String(this.selectedDiscussCompanyData.name || '').trim()
            ) {
              this.selectedDiscussCompanyData = null;
            }
            this.discussCompanySuggestionsOpen = true;
            this.fetchDiscussCompanySuggestions(query);
          },

          onDiscussCompanyFocus() {
            if (this.discussCompanyBlurTimer) {
                clearTimeout(this.discussCompanyBlurTimer);
            }
            if (this.discussCompanySuggestions.length > 0) {
                this.discussCompanySuggestionsOpen = true;
            }
          },

          onDiscussCompanyBlur() {
            if (this.discussCompanyBlurTimer) {
                clearTimeout(this.discussCompanyBlurTimer);
            }
            if (this.isDiscussCompanySuggestionInteracting) {
                this.isDiscussCompanySuggestionInteracting = false;
                return;
            }
            this.discussCompanyBlurTimer = setTimeout(() => {
                this.discussCompanySuggestionsOpen = false;
            }, 180);
          },

          startDiscussCompanySuggestionInteraction() {
            if (this.discussCompanyBlurTimer) {
                clearTimeout(this.discussCompanyBlurTimer);
            }
            this.isDiscussCompanySuggestionInteracting = true;
          },

          async selectDiscussCompanySuggestion(item) {
            if (!item) return;
            this.isDiscussCompanySuggestionInteracting = false;
            this.discussForm.company = item.value || '';
            this.selectedDiscussCompanyData = await this.enrichCompanySelection(item);
            this.discussCompanySuggestionsOpen = false;
            this.discussCompanySuggestions = [];
          },

          isEventInsideRef(event, refName) {
            const element = this.$refs[refName];
            if (!element) {
                return false;
            }
            if (typeof event.composedPath === 'function') {
                const path = event.composedPath();
                if (Array.isArray(path) && path.includes(element)) {
                    return true;
                }
            }
            return element.contains(event.target);
          },

          handleOutsideClick(event) {
            if (
                this.companySuggestionsOpen &&
                !this.isEventInsideRef(event, 'heroCompanySuggestionsWrapper')
            ) {
                this.isCompanySuggestionInteracting = false;
                this.companySuggestionsOpen = false;
            }
            if (
                this.discussCompanySuggestionsOpen &&
                !this.isEventInsideRef(event, 'discussCompanySuggestionsWrapper')
            ) {
                this.isDiscussCompanySuggestionInteracting = false;
                this.discussCompanySuggestionsOpen = false;
            }
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
            const companyPayload = this.buildCompanyPayload(company, this.selectedCompanyData);
            const direction = (this.direction || '').trim();
            this.isSending = true;
            try {
                await this.submitFormPayload('hero', {
                    name,
                    phone,
                    company,
                    ...companyPayload,
                    direction,
                    page: window.location.pathname,
                });
                this.sent = true;
            } catch (e) {
                console.error(e);
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
                await this.submitFormPayload('quiz', {
                    ...this.quizForm,
                    page: window.location.pathname,
                });
                this.quizSent = true;
            } catch (e) {
                console.error(e);
            } finally {
                this.isSendingQuiz = false;
            }
        },
        async submitPlanForm() {
            if (this.isSendingPlan || this.planSent) return;
            this.isSendingPlan = true;
            try {
                await this.submitFormPayload('plan', {
                    ...this.PlanForm,
                    ...this.buildCompanyPayload(this.PlanForm.company, null),
                    message: this.PlanForm.comment || '',
                    page: window.location.pathname,
                });
                this.planSent = true;
                this.PlanForm = { name: '', phone: '', company: '', comment: '' };
            } catch (e) {
                console.error(e);
            } finally {
                this.isSendingPlan = false;
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
                await this.submitFormPayload('discuss', {
                    ...this.discussForm,
                    ...this.buildCompanyPayload(this.discussForm.company, this.selectedDiscussCompanyData),
                    topic: this.discussTopic,
                    message: this.discussForm.comment || '',
                    page: window.location.pathname,
                });
                this.discussSent = true;
                this.discussForm = { name: '', phone: '', company: '', comment: '' };
                this.selectedDiscussCompanyData = null;
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
