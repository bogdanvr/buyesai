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
            companySuggestionPointerStartY: null,
            companySuggestionPointerMoved: false,
            pendingCompanySuggestion: null,
            lastCompanySuggestionSelectionKey: '',
            lastCompanySuggestionSelectionAt: 0,
            selectedCompanyData: null,
            heroCompanyDebug: {
                lastEvent: 'init',
                lastItemValue: '',
                lastItemInn: '',
                selectedInn: '',
                displayValue: '',
                suggestionsOpen: false,
                pointerDowns: 0,
                pointerUps: 0,
                clicks: 0,
                selectCalls: 0,
                logs: [],
            },
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
            discussCompanySuggestionPointerStartY: null,
            discussCompanySuggestionPointerMoved: false,
            pendingDiscussCompanySuggestion: null,
            lastDiscussCompanySuggestionSelectionKey: '',
            lastDiscussCompanySuggestionSelectionAt: 0,
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

          getItemValue(item) {
            return String((item && item.value) || '').trim();
          },

          getItemInn(item) {
            return String((item && item.inn) || '').trim();
          },

          getEventClientY(event) {
            if (event && typeof event.clientY === 'number') {
              return event.clientY;
            }
            if (
              event &&
              event.changedTouches &&
              event.changedTouches[0] &&
              typeof event.changedTouches[0].clientY === 'number'
            ) {
              return event.changedTouches[0].clientY;
            }
            return null;
          },

          pushHeroCompanyDebug(eventName, extra = {}) {
            const current = this.heroCompanyDebug || {};
            const next = {
              ...current,
              ...extra,
              lastEvent: eventName,
              selectedInn: String((this.selectedCompanyData && this.selectedCompanyData.inn) || '').trim(),
              displayValue: String(this.company || '').trim(),
              suggestionsOpen: !!this.companySuggestionsOpen,
            };
            const stamp = `${eventName} | item="${next.lastItemValue || ''}" | inn="${next.lastItemInn || ''}" | selected="${next.selectedInn || ''}" | value="${next.displayValue || ''}" | open=${next.suggestionsOpen}`;
            next.logs = [stamp, ...(Array.isArray(current.logs) ? current.logs : [])].slice(0, 8);
            this.heroCompanyDebug = next;
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

          formatSelectedCompanyLabel(selectedCompanyData, fallbackName = '') {
            const selected = this.normalizeSelectedCompanyData(selectedCompanyData, fallbackName);
            if (!selected || !selected.name) {
              return String(fallbackName || '').trim();
            }
            if (!selected.inn) {
              return selected.name;
            }
            return `${selected.name} (ИНН ${selected.inn})`;
          },

          isMatchingSelectedCompanyLabel(query, selectedCompanyData, fallbackName = '') {
            const normalizedQuery = String(query || '').trim();
            if (!normalizedQuery) {
              return false;
            }
            const selected = this.normalizeSelectedCompanyData(selectedCompanyData, fallbackName);
            if (!selected || !selected.name) {
              return false;
            }
            return normalizedQuery === selected.name || normalizedQuery === this.formatSelectedCompanyLabel(selected);
          },

          syncHeroCompanyDisplay() {
            if (!this.selectedCompanyData) {
              return;
            }
            this.company = this.formatSelectedCompanyLabel(this.selectedCompanyData, this.company);
          },

          syncDiscussCompanyDisplay() {
            if (!this.selectedDiscussCompanyData) {
              return;
            }
            this.discussForm.company = this.formatSelectedCompanyLabel(
              this.selectedDiscussCompanyData,
              this.discussForm.company,
            );
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
              !this.isMatchingSelectedCompanyLabel(query, this.selectedCompanyData, this.company)
            ) {
              this.selectedCompanyData = null;
            }
            this.companySuggestionsOpen = true;
            this.pushHeroCompanyDebug('input', {
              lastItemValue: '',
              lastItemInn: '',
            });
            this.fetchCompanySuggestions(query);
          },

          onCompanyFocus() {
            if (this.companyBlurTimer) {
                clearTimeout(this.companyBlurTimer);
            }
            if (this.selectedCompanyData && this.isMatchingSelectedCompanyLabel(this.company, this.selectedCompanyData, this.company)) {
                this.pushHeroCompanyDebug('focus-selected');
                return;
            }
            if (this.companySuggestions.length > 0) {
                this.companySuggestionsOpen = true;
            }
            this.pushHeroCompanyDebug('focus');
          },

          onCompanyBlur() {
            if (this.companyBlurTimer) {
                clearTimeout(this.companyBlurTimer);
            }
            if (this.isCompanySuggestionInteracting) {
                const pendingItem = this.pendingCompanySuggestion;
                this.isCompanySuggestionInteracting = false;
                if (pendingItem && !this.companySuggestionPointerMoved) {
                    this.pendingCompanySuggestion = null;
                    this.companySuggestionPointerStartY = null;
                    this.companySuggestionPointerMoved = false;
                    this.pushHeroCompanyDebug('blur-select-pending', {
                      lastItemValue: this.getItemValue(pendingItem),
                      lastItemInn: this.getItemInn(pendingItem),
                    });
                    this.selectCompanySuggestion(pendingItem, 'blur');
                }
                return;
            }
            this.companyBlurTimer = setTimeout(() => {
                this.syncHeroCompanyDisplay();
                this.companySuggestionsOpen = false;
                this.pushHeroCompanyDebug('blur-close');
            }, 180);
          },

          startCompanySuggestionInteraction(item = null) {
            if (this.companyBlurTimer) {
                clearTimeout(this.companyBlurTimer);
            }
            this.isCompanySuggestionInteracting = true;
            this.pendingCompanySuggestion = item || null;
            this.pushHeroCompanyDebug('interact-start', {
              lastItemValue: this.getItemValue(item),
              lastItemInn: this.getItemInn(item),
            });
          },

          isFocusedElement(element) {
            return !!(element && document.activeElement === element);
          },

          async handleCompanySuggestionPointerDown(event, item) {
            this.startCompanySuggestionPointer(event, item);
            const input = this.$refs.heroCompanyInput;
            const isTouchTap = !!(event && event.pointerType === 'touch');
            if (isTouchTap && this.isFocusedElement(input)) {
              if (event && typeof event.preventDefault === 'function') {
                event.preventDefault();
              }
              if (event && typeof event.stopPropagation === 'function') {
                event.stopPropagation();
              }
              this.pendingCompanySuggestion = null;
              this.companySuggestionPointerStartY = null;
              this.companySuggestionPointerMoved = false;
              await this.selectCompanySuggestion(item, 'pointerdown');
            }
          },

          startCompanySuggestionPointer(event, item) {
            this.startCompanySuggestionInteraction(item);
            const clientY = this.getEventClientY(event);
            this.companySuggestionPointerStartY = clientY;
            this.companySuggestionPointerMoved = false;
            this.pushHeroCompanyDebug('pointerdown', {
              lastItemValue: this.getItemValue(item),
              lastItemInn: this.getItemInn(item),
              pointerDowns: (this.heroCompanyDebug.pointerDowns || 0) + 1,
            });
          },

          moveCompanySuggestionPointer(event) {
            const clientY = this.getEventClientY(event);
            if (clientY === null || this.companySuggestionPointerStartY === null) {
              return;
            }
            if (Math.abs(clientY - this.companySuggestionPointerStartY) > 12) {
              this.companySuggestionPointerMoved = true;
            }
          },

          async endCompanySuggestionPointer(item) {
            this.pushHeroCompanyDebug('pointerup', {
              lastItemValue: this.getItemValue(item),
              lastItemInn: this.getItemInn(item),
              pointerUps: (this.heroCompanyDebug.pointerUps || 0) + 1,
            });
            if (this.companySuggestionPointerMoved) {
              this.isCompanySuggestionInteracting = false;
              this.pendingCompanySuggestion = null;
              this.companySuggestionPointerStartY = null;
              this.companySuggestionPointerMoved = false;
              this.pushHeroCompanyDebug('pointerup-moved', {
                lastItemValue: this.getItemValue(item),
                lastItemInn: this.getItemInn(item),
              });
              return;
            }
            this.pendingCompanySuggestion = null;
            this.companySuggestionPointerStartY = null;
            this.companySuggestionPointerMoved = false;
            await this.selectCompanySuggestion(item, 'pointerup');
          },

          cancelCompanySuggestionPointer() {
            this.isCompanySuggestionInteracting = false;
            this.pendingCompanySuggestion = null;
            this.companySuggestionPointerStartY = null;
            this.companySuggestionPointerMoved = false;
            this.pushHeroCompanyDebug('pointercancel');
          },

          async handleCompanySuggestionClick(item) {
            this.pushHeroCompanyDebug('click', {
              lastItemValue: this.getItemValue(item),
              lastItemInn: this.getItemInn(item),
              clicks: (this.heroCompanyDebug.clicks || 0) + 1,
            });
            await this.selectCompanySuggestion(item, 'click');
          },

          shouldSkipCompanySuggestionSelection(item) {
            const key = `${this.getItemValue(item)}:${this.getItemInn(item)}`;
            const now = Date.now();
            if (
              this.lastCompanySuggestionSelectionKey === key &&
              now - this.lastCompanySuggestionSelectionAt < 700
            ) {
              this.pushHeroCompanyDebug('select-skip', {
                lastItemValue: this.getItemValue(item),
                lastItemInn: this.getItemInn(item),
              });
              return true;
            }
            this.lastCompanySuggestionSelectionKey = key;
            this.lastCompanySuggestionSelectionAt = now;
            return false;
          },

          async selectCompanySuggestion(item, source = 'direct') {
            if (!item) return;
            if (this.shouldSkipCompanySuggestionSelection(item)) return;
            this.isCompanySuggestionInteracting = false;
            const selected = this.normalizeSelectedCompanyData(item, item.value || this.company);
            this.selectedCompanyData = selected;
            this.syncHeroCompanyDisplay();
            this.companySuggestionsOpen = false;
            this.companySuggestions = [];
            this.pushHeroCompanyDebug(`select-${source}`, {
              lastItemValue: this.getItemValue(item),
              lastItemInn: this.getItemInn(item),
              selectCalls: (this.heroCompanyDebug.selectCalls || 0) + 1,
            });
            this.$nextTick(() => {
              const input = this.$refs.heroCompanyInput;
              if (input && typeof input.blur === 'function') {
                input.blur();
              }
            });
            const enriched = await this.enrichCompanySelection(selected);
            if (
              this.selectedCompanyData &&
              String(this.selectedCompanyData.inn || '').trim() === String(selected.inn || '').trim() &&
              this.isMatchingSelectedCompanyLabel(this.company, selected, this.company)
            ) {
              this.selectedCompanyData = enriched;
              this.syncHeroCompanyDisplay();
              this.pushHeroCompanyDebug(`select-${source}-enriched`, {
                lastItemValue: this.getItemValue(item),
                lastItemInn: this.getItemInn(item),
              });
            }
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
              !this.isMatchingSelectedCompanyLabel(query, this.selectedDiscussCompanyData, this.discussForm.company)
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
            if (
              this.selectedDiscussCompanyData &&
              this.isMatchingSelectedCompanyLabel(
                this.discussForm.company,
                this.selectedDiscussCompanyData,
                this.discussForm.company,
              )
            ) {
                return;
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
                const pendingItem = this.pendingDiscussCompanySuggestion;
                this.isDiscussCompanySuggestionInteracting = false;
                if (pendingItem && !this.discussCompanySuggestionPointerMoved) {
                    this.pendingDiscussCompanySuggestion = null;
                    this.discussCompanySuggestionPointerStartY = null;
                    this.discussCompanySuggestionPointerMoved = false;
                    this.selectDiscussCompanySuggestion(pendingItem);
                }
                return;
            }
            this.discussCompanyBlurTimer = setTimeout(() => {
                this.syncDiscussCompanyDisplay();
                this.discussCompanySuggestionsOpen = false;
            }, 180);
          },

          startDiscussCompanySuggestionInteraction(item = null) {
            if (this.discussCompanyBlurTimer) {
                clearTimeout(this.discussCompanyBlurTimer);
            }
            this.isDiscussCompanySuggestionInteracting = true;
            this.pendingDiscussCompanySuggestion = item || null;
          },

          async handleDiscussCompanySuggestionPointerDown(event, item) {
            this.startDiscussCompanySuggestionPointer(event, item);
            const input = this.$refs.discussCompanyInput;
            const isTouchTap = !!(event && event.pointerType === 'touch');
            if (isTouchTap && this.isFocusedElement(input)) {
              if (event && typeof event.preventDefault === 'function') {
                event.preventDefault();
              }
              if (event && typeof event.stopPropagation === 'function') {
                event.stopPropagation();
              }
              this.pendingDiscussCompanySuggestion = null;
              this.discussCompanySuggestionPointerStartY = null;
              this.discussCompanySuggestionPointerMoved = false;
              await this.selectDiscussCompanySuggestion(item);
            }
          },

          startDiscussCompanySuggestionPointer(event, item) {
            this.startDiscussCompanySuggestionInteraction(item);
            const clientY = this.getEventClientY(event);
            this.discussCompanySuggestionPointerStartY = clientY;
            this.discussCompanySuggestionPointerMoved = false;
          },

          moveDiscussCompanySuggestionPointer(event) {
            const clientY = this.getEventClientY(event);
            if (clientY === null || this.discussCompanySuggestionPointerStartY === null) {
              return;
            }
            if (Math.abs(clientY - this.discussCompanySuggestionPointerStartY) > 12) {
              this.discussCompanySuggestionPointerMoved = true;
            }
          },

          async endDiscussCompanySuggestionPointer(item) {
            if (this.discussCompanySuggestionPointerMoved) {
              this.isDiscussCompanySuggestionInteracting = false;
              this.pendingDiscussCompanySuggestion = null;
              this.discussCompanySuggestionPointerStartY = null;
              this.discussCompanySuggestionPointerMoved = false;
              return;
            }
            this.pendingDiscussCompanySuggestion = null;
            this.discussCompanySuggestionPointerStartY = null;
            this.discussCompanySuggestionPointerMoved = false;
            await this.selectDiscussCompanySuggestion(item);
          },

          cancelDiscussCompanySuggestionPointer() {
            this.isDiscussCompanySuggestionInteracting = false;
            this.pendingDiscussCompanySuggestion = null;
            this.discussCompanySuggestionPointerStartY = null;
            this.discussCompanySuggestionPointerMoved = false;
          },

          shouldSkipDiscussCompanySuggestionSelection(item) {
            const key = `${this.getItemValue(item)}:${this.getItemInn(item)}`;
            const now = Date.now();
            if (
              this.lastDiscussCompanySuggestionSelectionKey === key &&
              now - this.lastDiscussCompanySuggestionSelectionAt < 700
            ) {
              return true;
            }
            this.lastDiscussCompanySuggestionSelectionKey = key;
            this.lastDiscussCompanySuggestionSelectionAt = now;
            return false;
          },

          async selectDiscussCompanySuggestion(item) {
            if (!item) return;
            if (this.shouldSkipDiscussCompanySuggestionSelection(item)) return;
            this.isDiscussCompanySuggestionInteracting = false;
            const selected = this.normalizeSelectedCompanyData(item, item.value || this.discussForm.company);
            this.selectedDiscussCompanyData = selected;
            this.syncDiscussCompanyDisplay();
            this.discussCompanySuggestionsOpen = false;
            this.discussCompanySuggestions = [];
            this.$nextTick(() => {
              const input = this.$refs.discussCompanyInput;
              if (input && typeof input.blur === 'function') {
                input.blur();
              }
            });
            const enriched = await this.enrichCompanySelection(selected);
            if (
              this.selectedDiscussCompanyData &&
              String(this.selectedDiscussCompanyData.inn || '').trim() === String(selected.inn || '').trim() &&
              this.isMatchingSelectedCompanyLabel(this.discussForm.company, selected, this.discussForm.company)
            ) {
              this.selectedDiscussCompanyData = enriched;
              this.syncDiscussCompanyDisplay();
            }
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
