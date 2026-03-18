    const { createApp } = Vue;

    const SECTION_ENDPOINTS = {
      leads: "/api/v1/leads/?page_size=100",
      deals: "/api/v1/deals/?page_size=100",
      contacts: "/api/v1/contacts/?page_size=100",
      companies: "/api/v1/clients/?page_size=100",
      tasks: "/api/v1/activities/?type=task&page_size=100",
      touches: "/api/v1/touches/?page_size=100"
    };

    const LEAD_STATUS_LABELS = {
      new: "Новый",
      in_progress: "В работе",
      attempting_contact: "Попытка контакта",
      qualified: "Квалифицирован",
      unqualified: "Неквалифицирован",
      converted: "Конвертирован",
      lost: "Потерян",
      spam: "Спам",
      archived: "В архиве"
    };

    const LEAD_STATUS_MAIN_FLOW_NEXT = {
      new: "in_progress",
      in_progress: "attempting_contact",
      attempting_contact: "qualified",
      qualified: "converted"
    };

    const TASK_STATUS_OPTIONS = [
      { value: "todo", label: "К выполнению" },
      { value: "in_progress", label: "В работе" },
      { value: "done", label: "Выполнено" },
      { value: "canceled", label: "Отменено" }
    ];

    const TASK_PRIORITY_OPTIONS = [
      { value: "low", label: "Низкий" },
      { value: "medium", label: "Средний" },
      { value: "high", label: "Высокий" }
    ];

    createApp({
      delimiters: ["[[", "]]"],
      data() {
        return {
          activeSection: "leads",
          search: "",
          showModal: false,
          isLoading: false,
          isSaving: false,
          showStatusFilter: false,
          selectedStatusFilters: [],
          editingLeadId: null,
          editingDealId: null,
          editingContactId: null,
          editingCompanyId: null,
          editingTaskId: null,
          editingTouchId: null,
          showAllLeadFields: false,
          showAllDealFields: false,
          isDealTaskSaving: false,
          isDealTasksLoading: false,
          showDealTaskForm: false,
          isDealCompanySaving: false,
          isSourceSaving: false,
          showDealCompanyForm: false,
          showDealContactsPanel: false,
          showDealContactForm: false,
          isDealContactsLoading: false,
          isCompanyContactSaving: false,
          isCompanyContactsLoading: false,
          isTaskTouchesLoading: false,
          showCompanyContactForm: false,
          showCompanyNoteDraft: false,
          showCompanyOkvedDetails: false,
          showAllCompanyFields: false,
          showAllTaskFields: false,
          expandedCompanyCards: {},
          showCompanyEvents: false,
          taskDealFilterId: null,
          taskDealFilterLabel: "",
          taskTouchOptions: [],
          showSourceCreateForm: false,
          sourceCreateTargetSection: "",
          sourceCreateForm: {
            name: ""
          },
          errorMessage: "",
          modalErrorMessage: "",
          forms: {
            leads: {
              title: "",
              description: "",
              name: "",
              company: "",
              phone: "",
              email: "",
              assignedToId: null,
              priority: "medium",
              expectedValue: "",
              statusId: "",
              sourceId: "",
              sourceName: "",
              sourceCode: "",
              sourceNames: [],
              history: [],
              websiteSessionId: ""
            },
            deals: {
              title: "",
              description: "",
              sourceId: "",
              companyId: null,
              ownerId: null,
              amount: "0",
              closeDate: "",
              stageId: "",
              failureReason: "",
              events: ""
            },
            contacts: {
              fullName: "",
              companyId: null,
              position: "",
              phone: "",
              email: "",
              isPrimary: false
            },
            companies: {
              name: "",
              legalName: "",
              inn: "",
              address: "",
              industry: "",
              okved: "",
              okveds: [],
              phone: "",
              email: "",
              currency: "RUB",
              website: "",
              workRules: {
                decisionMakerId: null,
                communicationChannelIds: [],
                paymentTerms: "",
                documentRequirements: "",
                approvalCycle: "",
                risks: "",
                preferences: "",
              },
              notes: "",
              noteDraft: "",
              events: "",
              isActive: true
            },
            tasks: {
              subject: "",
              taskTypeId: null,
              priority: "medium",
              companyId: null,
              dealId: null,
              relatedTouchId: null,
              dueAt: "",
              reminderOffsetMinutes: 30,
              description: "",
              result: "",
              saveCompanyNote: false,
              companyNote: "",
              status: "todo"
            },
            touches: {
              happenedAt: "",
              channelId: null,
              direction: "outgoing",
              result: "",
              summary: "",
              nextStep: "",
              nextStepAt: "",
              ownerId: null,
              companyId: null,
              contactId: null,
              taskId: null,
              leadId: null,
              dealId: null
            }
          },
          dealTaskForm: {
            subject: "",
            dueAt: "",
            description: ""
          },
          taskFollowUpForm: {
            subject: "",
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          },
          dealCompanyForm: {
            name: "",
            inn: "",
            address: "",
            industry: "",
            okved: "",
            phone: "",
            email: "",
            currency: "RUB",
            website: ""
          },
          dealCompanyContactForm: {
            fullName: "",
            position: "",
            phone: "",
            email: "",
            isPrimary: true
          },
          dealTasksForActiveDeal: [],
          dealCompanyContacts: [],
          companyContactForm: {
            fullName: "",
            position: "",
            phone: "",
            email: "",
            isPrimary: false
          },
          companyContactsForActiveCompany: [],
          metaOptions: {
            leadStatuses: [],
            dealStages: [],
            leadSources: [],
            users: [],
            taskTypes: [],
            communicationChannels: [],
            currencyRates: { RUB: 1 }
          },
          taskStatusOptions: TASK_STATUS_OPTIONS,
          taskPriorityOptions: TASK_PRIORITY_OPTIONS,
          taskReminderOptions: [
            { value: 5, label: "5 минут" },
            { value: 10, label: "10 минут" },
            { value: 15, label: "15 минут" },
            { value: 30, label: "30 минут" },
            { value: 60, label: "1 час" },
            { value: 120, label: "2 часа" },
            { value: 180, label: "3 часа" }
          ],
          sidebarItems: [
            { key: "leads", label: "Лиды", shortLabel: "Лиды", icon: "◎" },
            { key: "deals", label: "Сделки", shortLabel: "Сделки", icon: "◔" },
            { key: "contacts", label: "Контакты", shortLabel: "Контакты", icon: "◉" },
            { key: "companies", label: "Компании", shortLabel: "Компании", icon: "▣" },
            { key: "tasks", label: "Задачи", shortLabel: "Задачи", icon: "✓" },
            { key: "touches", label: "Касания", shortLabel: "Касания", icon: "◌" }
          ],
          datasets: {
            leads: [],
            deals: [],
            contacts: [],
            companies: [],
            tasks: [],
            touches: []
          }
        };
      },
      computed: {
        currentSectionTitle() {
          const titles = {
            leads: "Все лиды",
            deals: "Все сделки",
            contacts: "Все контакты",
            companies: "Все компании",
            tasks: "Все задачи",
            touches: "Все касания"
          };
          return titles[this.activeSection] || "CRM";
        },
        createButtonLabel() {
          const labels = {
            leads: "лид",
            deals: "сделку",
            contacts: "контакт",
            companies: "компанию",
            tasks: "задачу",
            touches: "касание"
          };
          return labels[this.activeSection] || "элемент";
        },
        createModalSubtitle() {
          if (this.editingLeadId && this.activeSection === "leads") {
            return "Редактирование лида";
          }
          if (this.editingDealId && this.activeSection === "deals") {
            return "Редактирование сделки";
          }
          if (this.editingContactId && this.activeSection === "contacts") {
            return "Редактирование контакта";
          }
          if (this.editingCompanyId && this.activeSection === "companies") {
            return "Редактирование компании";
          }
          if (this.editingTaskId && this.activeSection === "tasks") {
            return "Редактирование задачи";
          }
          if (this.editingTouchId && this.activeSection === "touches") {
            return "Редактирование касания";
          }
          const titles = {
            leads: "Создание лида",
            deals: "Создание сделки",
            contacts: "Создание контакта",
            companies: "Создание компании",
            tasks: "Создание задачи",
            touches: "Создание касания"
          };
          return titles[this.activeSection] || "Создание элемента";
        },
        modalTitle() {
          if (this.editingLeadId && this.activeSection === "leads") {
            return "Редактировать лид";
          }
          if (this.editingDealId && this.activeSection === "deals") {
            return "Редактировать сделку";
          }
          if (this.editingContactId && this.activeSection === "contacts") {
            return "Редактировать контакт";
          }
          if (this.editingCompanyId && this.activeSection === "companies") {
            return "Редактировать компанию";
          }
          if (this.editingTaskId && this.activeSection === "tasks") {
            return "Редактировать задачу";
          }
          if (this.editingTouchId && this.activeSection === "touches") {
            return "Редактировать касание";
          }
          return `Добавить ${this.createButtonLabel}`;
        },
        modalSubmitLabel() {
          if (this.editingLeadId && this.activeSection === "leads") {
            return "Сохранить изменения";
          }
          if (this.editingDealId && this.activeSection === "deals") {
            return "Сохранить сделку";
          }
          if (this.editingContactId && this.activeSection === "contacts") {
            return "Сохранить контакт";
          }
          if (this.editingCompanyId && this.activeSection === "companies") {
            return "Сохранить компанию";
          }
          if (this.editingTaskId && this.activeSection === "tasks") {
            return "Сохранить задачу";
          }
          if (this.editingTouchId && this.activeSection === "touches") {
            return "Сохранить касание";
          }
          return "Сохранить";
        },
        fieldEditToggleLabel() {
          if (this.activeSection === "leads") {
            return this.showAllLeadFields ? "Скрыть" : "Редактировать";
          }
          if (this.activeSection === "deals") {
            return this.showAllDealFields ? "Скрыть" : "Редактировать";
          }
          if (this.activeSection === "companies") {
            return this.showAllCompanyFields ? "Скрыть" : "Редактировать";
          }
          if (this.activeSection === "tasks") {
            return this.showAllTaskFields ? "Скрыть" : "Редактировать";
          }
          return "Редактировать";
        },
        companyOptions() {
          return this.datasets.companies.map((company) => ({
            id: company.id,
            name: company.name,
          }));
        },
        isCreatingCompany() {
          return this.activeSection === "companies" && !this.editingCompanyId;
        },
        isCreatingLead() {
          return this.activeSection === "leads" && !this.editingLeadId;
        },
        isCreatingDeal() {
          return this.activeSection === "deals" && !this.editingDealId;
        },
        isCreatingTask() {
          return this.activeSection === "tasks" && !this.editingTaskId;
        },
        touchLeadOptions() {
          return this.datasets.leads.map((lead) => ({ id: lead.id, title: lead.title || lead.name }));
        },
        touchDealOptions() {
          return this.datasets.deals.map((deal) => ({ id: deal.id, title: deal.title || deal.name }));
        },
        touchContactOptions() {
          return this.datasets.contacts.map((contact) => ({ id: contact.id, title: contact.fullName || contact.name }));
        },
        touchTaskOptions() {
          return this.datasets.tasks.map((task) => ({ id: task.id, title: task.subject || task.name }));
        },
        dealHasSelectedCompany() {
          return !!this.toIntOrNull(this.forms.deals.companyId);
        },
        dealSelectedCompanyName() {
          const companyId = this.toIntOrNull(this.forms.deals.companyId);
          if (!companyId) return "";
          const selected = this.datasets.companies.find((company) => String(company.id) === String(companyId));
          return selected ? selected.name : `Компания #${companyId}`;
        },
        isDealFailedStageSelected() {
          return this.resolveDealStageCode(this.forms.deals.stageId) === "failed";
        },
        canSubmitDealCompanyAction() {
          return !!this.dealCompanyForm.name.trim();
        },
        shouldShowCompanyField() {
          return (value) => this.isCreatingCompany || this.showAllCompanyFields || !!String(value || "").trim();
        },
        shouldShowLeadField() {
          return (value) => this.isCreatingLead || this.showAllLeadFields || this.hasVisibleFieldValue(value);
        },
        shouldShowDealField() {
          return (value) => this.isCreatingDeal || this.showAllDealFields || this.hasVisibleFieldValue(value);
        },
        shouldShowTaskField() {
          return (value) => this.isCreatingTask || this.showAllTaskFields || this.hasVisibleFieldValue(value);
        },
        shouldShowLeadTrackingBlock() {
          return this.isCreatingLead
            || this.showAllLeadFields
            || !!this.forms.leads.websiteSessionId
            || this.forms.leads.sourceNames.length > 0
            || this.forms.leads.history.length > 0;
        },
        showFieldEditToggle() {
          return (
            (this.activeSection === "leads" && !!this.editingLeadId)
            || (this.activeSection === "deals" && !!this.editingDealId)
            || (this.activeSection === "companies" && !!this.editingCompanyId)
            || (this.activeSection === "tasks" && !!this.editingTaskId)
          );
        },
        showTaskResultField() {
          return this.isTaskDoneStatus(this.forms.tasks.status) || !!String(this.forms.tasks.result || "").trim();
        },
        taskActiveDeal() {
          const dealId = this.toIntOrNull(this.forms.tasks.dealId);
          if (!dealId) return null;
          return this.datasets.deals.find((deal) => String(deal.id) === String(dealId)) || null;
        },
        taskActiveDealRequiresFollowUp() {
          const deal = this.taskActiveDeal;
          if (!deal) return false;
          const stageCode = String(deal.stageCode || "").trim().toLowerCase();
          return !["won", "failed"].includes(stageCode);
        },
        showTaskFollowUpSuggestion() {
          return !!this.editingTaskId && this.isTaskDoneStatus(this.forms.tasks.status) && this.taskActiveDealRequiresFollowUp;
        },
        taskFollowUpDealTitle() {
          return this.taskActiveDeal ? this.taskActiveDeal.title || this.taskActiveDeal.name : "";
        },
        emptyLabel() {
          const labels = {
            leads: "лидов",
            deals: "сделок",
            contacts: "контактов",
            companies: "компаний",
            tasks: "задач"
          };
          return labels[this.activeSection] || "элементов";
        },
        emptySuffix() {
          return this.activeSection === "contacts" ? "о" : "";
        },
        currentItems() {
          return this.datasets[this.activeSection] || [];
        },
        filteredItems() {
          const q = this.search.trim().toLowerCase();
          const filtered = this.currentItems.filter((item) => {
            const matchesDealFilter =
              this.activeSection !== "tasks" ||
              !this.taskDealFilterId ||
              String(item.dealId || "") === String(this.taskDealFilterId);
            const matchesSearch = !q || [item.name, item.company, item.deal, item.phone, item.email, item.statusLabel]
              .filter(Boolean)
              .some((value) => String(value).toLowerCase().includes(q));
            const matchesStatus =
              !this.selectedStatusFilters.length ||
              this.selectedStatusFilters.includes(item.statusLabel);
            return matchesDealFilter && matchesSearch && matchesStatus;
          });
          const ordered = filtered.map((item, index) => ({ item, index }));
          ordered.sort((left, right) => {
            const leftTop = this.isTopPriorityItem(left.item);
            const rightTop = this.isTopPriorityItem(right.item);
            if (leftTop !== rightTop) {
              return leftTop ? -1 : 1;
            }

            const leftRank = this.getSortRank(left.item);
            const rightRank = this.getSortRank(right.item);
            if (leftRank !== rightRank) {
              return leftRank - rightRank;
            }

            if (this.activeSection === "tasks" && leftRank === 0 && rightRank === 0) {
              const taskOrder = this.compareActiveTasksByDueAt(left.item, right.item);
              if (taskOrder !== 0) {
                return taskOrder;
              }
            }
            return left.index - right.index;
          });
          return ordered.map((entry) => entry.item);
        },
        statusFilterOptions() {
          const labels = new Set(
            (this.currentItems || [])
              .map((item) => item.statusLabel)
              .filter(Boolean)
          );
          return Array.from(labels)
            .sort((a, b) => String(a).localeCompare(String(b), "ru"))
            .map((label) => ({ value: label, label }));
        },
        stats() {
          const items = this.filteredItems;
          const newItems = items.filter((item) => this.getItemStatusBucket(item) === "new");
          const inProgressItems = items.filter((item) => this.getItemStatusBucket(item) === "progress");
          const doneItems = items.filter((item) => this.getItemStatusBucket(item) === "done");
          return {
            totalCount: items.length,
            totalAmountRub: this.sumItemsAmountRub(items),
            newCount: newItems.length,
            newAmountRub: this.sumItemsAmountRub(newItems),
            inProgressCount: inProgressItems.length,
            inProgressAmountRub: this.sumItemsAmountRub(inProgressItems),
            doneCount: doneItems.length,
            doneAmountRub: this.sumItemsAmountRub(doneItems)
          };
        },
        companyStats() {
          if (this.activeSection !== "companies") {
            return {
              totalCount: 0,
              activeCount: 0,
              inProgressCount: 0,
            };
          }

          const companies = this.filteredItems;
          return {
            totalCount: companies.length,
            activeCount: companies.filter((item) => item.isActive !== false).length,
            inProgressCount: companies.filter((item) => this.companyHasActiveDeals(item.id)).length,
          };
        },
        showStatsAmount() {
          return this.activeSection === "leads" || this.activeSection === "deals";
        },
        taskFormRemainingLabel() {
          return this.formatTaskRemainingLabel(this.forms.tasks.dueAt, this.forms.tasks.status);
        },
        taskTouchSelectOptions() {
          return Array.isArray(this.taskTouchOptions) ? this.taskTouchOptions : [];
        }
      },
      watch: {
        "forms.tasks.dealId": {
          handler() {
            if (this.activeSection === "tasks" && this.showModal) {
              this.loadTaskTouchOptions();
            }
          }
        },
        "forms.tasks.companyId": {
          handler() {
            if (this.activeSection === "tasks" && this.showModal) {
              this.loadTaskTouchOptions();
            }
          }
        }
      },
      methods: {
        getCsrfToken() {
          const cookie = document.cookie || "";
          const parts = cookie.split(";").map((x) => x.trim());
          const target = parts.find((x) => x.startsWith("csrftoken="));
          return target ? decodeURIComponent(target.split("=")[1]) : "";
        },
        ensurePhonePrefix(target, field = "phone") {
          if (!target || typeof target !== "object") return;
          const current = String(target[field] || "").trim();
          if (!current) {
            target[field] = "+7";
          }
        },
        clearZeroOnFocus(target, field) {
          if (!target || typeof target !== "object") return;
          const current = String(target[field] || "").trim();
          if (current === "0" || current === "0.0" || current === "0.00") {
            target[field] = "";
          }
        },
        setUiError(message, options = {}) {
          const useModal = options.modal === true || (options.modal !== false && this.showModal);
          if (useModal) {
            this.modalErrorMessage = message;
            return;
          }
          this.errorMessage = message;
        },
        clearUiErrors(options = {}) {
          if (!options.globalOnly) {
            this.modalErrorMessage = "";
          }
          if (!options.modalOnly) {
            this.errorMessage = "";
          }
        },
        phoneHref(value) {
          const normalized = String(value || "").trim().replace(/[^\d+]/g, "");
          return normalized ? `tel:${normalized}` : "";
        },
        normalizePaginatedResponse(data) {
          if (Array.isArray(data)) return data;
          if (data && Array.isArray(data.results)) return data.results;
          return [];
        },
        hasVisibleFieldValue(value) {
          if (Array.isArray(value)) {
            return value.length > 0;
          }
          if (value && typeof value === "object") {
            return Object.keys(value).length > 0;
          }
          if (typeof value === "number") {
            return value !== 0;
          }
          return !!String(value || "").trim();
        },
        toggleFieldEditMode() {
          if (this.activeSection === "leads") {
            this.showAllLeadFields = !this.showAllLeadFields;
            return;
          }
          if (this.activeSection === "deals") {
            this.showAllDealFields = !this.showAllDealFields;
            return;
          }
          if (this.activeSection === "companies") {
            this.showAllCompanyFields = !this.showAllCompanyFields;
            return;
          }
          if (this.activeSection === "tasks") {
            this.showAllTaskFields = !this.showAllTaskFields;
          }
        },
        isFieldEditModeActive() {
          if (this.activeSection === "leads") {
            return this.showAllLeadFields;
          }
          if (this.activeSection === "deals") {
            return this.showAllDealFields;
          }
          if (this.activeSection === "companies") {
            return this.showAllCompanyFields;
          }
          if (this.activeSection === "tasks") {
            return this.showAllTaskFields;
          }
          return false;
        },
        parseEventLog(value) {
          const raw = String(value || "").trim();
          if (!raw) return [];

          return raw
            .split(/\n\s*\n+/)
            .map((chunk) => String(chunk || "").trim())
            .filter(Boolean)
            .map((chunk) => {
              const lines = chunk
                .split("\n")
                .map((line) => String(line || "").trim())
                .filter(Boolean);
              if (!lines.length) {
                return null;
              }

              const firstLine = lines[0];
              const timestampPattern = /^\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}$/;
              const eventItem = {
                timestamp: timestampPattern.test(firstLine) ? firstLine : "",
                result: "",
                taskId: null,
                dealId: null,
                extra: "",
              };
              const contentLines = eventItem.timestamp ? lines.slice(1) : lines.slice();
              const extraLines = [];

              contentLines.forEach((line) => {
                if (!line) return;
                if (line.indexOf("Результат:") === 0) {
                  eventItem.result = line.replace(/^Результат:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("task_id:") === 0) {
                  const parsedTaskId = Number.parseInt(line.replace(/^task_id:\s*/u, "").trim(), 10);
                  eventItem.taskId = Number.isNaN(parsedTaskId) ? null : parsedTaskId;
                  return;
                }
                if (line.indexOf("deal_id:") === 0) {
                  const parsedDealId = Number.parseInt(line.replace(/^deal_id:\s*/u, "").trim(), 10);
                  eventItem.dealId = Number.isNaN(parsedDealId) ? null : parsedDealId;
                  return;
                }
                extraLines.push(line);
              });

              if (!eventItem.result && !eventItem.taskId && !eventItem.dealId) {
                return {
                  timestamp: eventItem.timestamp,
                  result: contentLines.join("\n") || chunk,
                  taskId: null,
                  dealId: null,
                  extra: "",
                };
              }

              eventItem.extra = extraLines.join("\n").trim();
              return eventItem;
            })
            .filter(Boolean);
        },
        trackingEventLabel(value) {
          const labels = {
            page_view: "Просмотр страницы",
            chat_opened: "Открытие чата",
            first_message_sent: "Первое сообщение",
            form_submitted: "Отправка формы",
            phone_clicked: "Клик по телефону",
            messenger_clicked: "Клик по мессенджеру",
          };
          const normalized = String(value || "").trim();
          return labels[normalized] || normalized || "Событие";
        },
        humanizeActivityType(value) {
          const labels = {
            call: "звонок",
            email: "email",
            meeting: "встреча",
            note: "заметка",
            task: "задача",
          };
          const normalized = String(value || "").trim();
          return labels[normalized] || normalized || "активность";
        },
        formatHistoryTimestamp(value) {
          const raw = String(value || "").trim();
          if (!raw) return "";
          const parsed = new Date(raw);
          if (Number.isNaN(parsed.getTime())) {
            return raw;
          }
          return parsed.toLocaleString("ru-RU", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });
        },
        formatEventTimestamp(value) {
          const raw = String(value || "").trim();
          if (!raw) return "";
          if (/^\d{2}\.\d{2}\.\d{4}(\s+\d{2}:\d{2})?$/.test(raw)) {
            return raw;
          }
          const parsed = new Date(raw);
          if (Number.isNaN(parsed.getTime())) {
            return raw;
          }
          return parsed.toLocaleString("ru-RU", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });
        },
        humanizeLeadSourceName(value) {
          const raw = String(value || "").trim();
          if (!raw) return "";
          if (raw.indexOf("Источник трафика:") === 0) {
            return raw.replace(/^Источник трафика:\s*/u, "").trim();
          }
          if (raw.indexOf("Форма сайта:") === 0) {
            return `клик по форме ${raw.replace(/^Форма сайта:\s*/u, "").trim()}`;
          }
          if (raw.indexOf("Действие:") === 0) {
            return raw.replace(/^Действие:\s*/u, "").trim();
          }
          return raw;
        },
        leadEventPathLabel(item) {
          if (!item || typeof item !== "object") return "";
          const eventCode = String(item.event || "").trim();
          if (eventCode === "chat_opened") {
            return "клик по чату";
          }
          if (eventCode === "first_message_sent") {
            return "первое сообщение";
          }
          if (eventCode === "phone_clicked") {
            return "клик по телефону";
          }
          if (eventCode === "messenger_clicked") {
            return "клик по мессенджеру";
          }
          if (eventCode === "form_submitted") {
            const formType = String(item.form_type || "").trim();
            return formType ? `клик по форме ${formType}` : "отправка формы";
          }
          return "";
        },
        leadSourcePath(leadForm) {
          const form = leadForm && typeof leadForm === "object" ? leadForm : {};
          const path = [];
          const pushUnique = (value) => {
            const normalized = String(value || "").trim();
            if (!normalized || path.includes(normalized)) return;
            path.push(normalized);
          };

          if (form.sourceName) {
            pushUnique(this.humanizeLeadSourceName(form.sourceName));
          }

          const history = Array.isArray(form.history) ? form.history : [];
          history.forEach((historyItem) => {
            const eventLabel = this.leadEventPathLabel(historyItem);
            if (eventLabel) {
              pushUnique(eventLabel);
            }
          });

          const sourceNames = Array.isArray(form.sourceNames) ? form.sourceNames : [];
          sourceNames.forEach((sourceName) => {
            const humanized = this.humanizeLeadSourceName(sourceName);
            if (humanized && humanized.indexOf("клик по форме ") === 0) {
              pushUnique(humanized);
            }
          });

          return path;
        },
        async fetchTaskById(taskId) {
          const normalizedTaskId = this.toIntOrNull(taskId);
          if (!normalizedTaskId) {
            throw new Error("Некорректный ID задачи");
          }

          const existingTask = this.datasets.tasks.find((item) => String(item.id) === String(normalizedTaskId));
          if (existingTask) {
            return existingTask;
          }

          const payload = await this.apiRequest(`/api/v1/activities/${normalizedTaskId}/`);
          return this.mapTask(payload);
        },
        async fetchDealById(dealId) {
          const normalizedDealId = this.toIntOrNull(dealId);
          if (!normalizedDealId) {
            throw new Error("Некорректный ID сделки");
          }

          const existingDeal = this.datasets.deals.find((item) => String(item.id) === String(normalizedDealId));
          if (existingDeal) {
            return existingDeal;
          }

          const payload = await this.apiRequest(`/api/v1/deals/${normalizedDealId}/`);
          return this.mapDeal(payload);
        },
        async openTaskFromEvent(taskId) {
          try {
            const task = await this.fetchTaskById(taskId);
            this.openTaskEditor(task);
          } catch (error) {
            this.errorMessage = `Ошибка открытия задачи: ${error.message}`;
          }
        },
        async openDealFromEvent(dealId) {
          try {
            const deal = await this.fetchDealById(dealId);
            this.openDealEditor(deal);
          } catch (error) {
            this.errorMessage = `Ошибка открытия сделки: ${error.message}`;
          }
        },
        sortDealStages(stages) {
          return [...(Array.isArray(stages) ? stages : [])].sort((left, right) => {
            const leftOrder = Number.parseInt(left && left.order, 10);
            const rightOrder = Number.parseInt(right && right.order, 10);
            const safeLeftOrder = Number.isNaN(leftOrder) ? 9999 : leftOrder;
            const safeRightOrder = Number.isNaN(rightOrder) ? 9999 : rightOrder;
            if (safeLeftOrder !== safeRightOrder) {
              return safeLeftOrder - safeRightOrder;
            }

            const leftFinal = !!(left && left.is_final);
            const rightFinal = !!(right && right.is_final);
            if (leftFinal !== rightFinal) {
              return leftFinal ? 1 : -1;
            }

            return String((left && left.name) || "").localeCompare(String((right && right.name) || ""), "ru");
          });
        },
        resolveDealWonFlag(stageId) {
          const normalizedStageId = this.toIntOrNull(stageId);
          if (!normalizedStageId) return false;
          const stage = this.metaOptions.dealStages.find(
            (candidate) => String(candidate.id) === String(normalizedStageId)
          );
          return String((stage && stage.code) || "").toLowerCase() === "won";
        },
        resolveDealStageCode(stageId) {
          const normalizedStageId = this.toIntOrNull(stageId);
          if (!normalizedStageId) return "";
          const stage = this.metaOptions.dealStages.find(
            (candidate) => String(candidate.id) === String(normalizedStageId)
          );
          return String((stage && stage.code) || "").trim().toLowerCase();
        },
        normalizeCompanyWorkRules(value = {}) {
          const payload = value && typeof value === "object" ? value : {};
          const rawCommunicationChannelIds = Array.isArray(payload.communication_channels)
            ? payload.communication_channels
            : (payload.communication_channel !== undefined && payload.communication_channel !== null
              ? [payload.communication_channel]
              : (Array.isArray(payload.communicationChannelIds)
                ? payload.communicationChannelIds
                : (payload.communicationChannelId ? [payload.communicationChannelId] : [])));
          return {
            decisionMakerId: this.toIntOrNull(payload.decision_maker_contact || payload.decisionMakerId),
            communicationChannelIds: rawCommunicationChannelIds
              .map((item) => this.toIntOrNull(item))
              .filter((item, index, items) => item && items.indexOf(item) === index),
            paymentTerms: String(payload.payment_terms || payload.paymentTerms || "").trim(),
            documentRequirements: String(payload.document_requirements || payload.documentRequirements || "").trim(),
            approvalCycle: String(payload.approval_cycle || payload.approvalCycle || "").trim(),
            risks: String(payload.risks || "").trim(),
            preferences: String(payload.preferences || "").trim(),
          };
        },
        serializeCompanyWorkRules(value = {}) {
          const normalized = this.normalizeCompanyWorkRules(value);
          const result = {};
          if (normalized.decisionMakerId) result.decision_maker_contact = normalized.decisionMakerId;
          if (normalized.communicationChannelIds.length) result.communication_channels = normalized.communicationChannelIds;
          if (normalized.paymentTerms) result.payment_terms = normalized.paymentTerms;
          if (normalized.documentRequirements) result.document_requirements = normalized.documentRequirements;
          if (normalized.approvalCycle) result.approval_cycle = normalized.approvalCycle;
          if (normalized.risks) result.risks = normalized.risks;
          if (normalized.preferences) result.preferences = normalized.preferences;
          return result;
        },
        resolveDefaultLeadStatusId() {
          const preferredStatus = this.metaOptions.leadStatuses.find(
            (status) => String((status && status.code) || "").trim().toLowerCase() === "new"
          );
          return preferredStatus ? preferredStatus.id : (this.metaOptions.leadStatuses.length ? this.metaOptions.leadStatuses[0].id : "");
        },
        extractErrorMessage(data, fallback) {
          if (!data) return fallback;
          if (typeof data === "string") return data;
          if (typeof data.detail === "string") return data.detail;
          const entries = Object.entries(data);
          if (!entries.length) return fallback;
          const [field, value] = entries[0];
          if (Array.isArray(value)) {
            return `${field}: ${value.join(", ")}`;
          }
          return `${field}: ${String(value)}`;
        },
        toggleCompanyEvents() {
          this.showCompanyEvents = !this.showCompanyEvents;
        },
        toggleCompanyNoteDraft() {
          this.showCompanyNoteDraft = !this.showCompanyNoteDraft;
          if (!this.showCompanyNoteDraft) {
            this.forms.companies.noteDraft = "";
          }
        },
        async apiRequest(url, options = {}) {
          const headers = { ...(options.headers || {}) };
          const hasBody = options.body !== undefined;
          if (hasBody) {
            headers["Content-Type"] = "application/json";
            headers["X-CSRFToken"] = this.getCsrfToken();
          }
          const response = await fetch(url, {
            method: options.method || "GET",
            credentials: "same-origin",
            headers,
            body: hasBody ? JSON.stringify(options.body) : undefined
          });
          let payload = null;
          try {
            payload = await response.json();
          } catch (_) {
            payload = null;
          }
          if (!response.ok) {
            const message = this.extractErrorMessage(payload, `HTTP ${response.status}`);
            throw new Error(message);
          }
          return payload;
        },
        uiStatus(status, fallbackLabel = "") {
          if (status === "done") return { status: "done", label: fallbackLabel || "Завершено" };
          if (status === "new") return { status: "new", label: fallbackLabel || "Новый" };
          return { status: "progress", label: fallbackLabel || "В работе" };
        },
        taskStatusMeta(status) {
          const normalized = String(status || "todo").trim();
          return this.taskStatusOptions.find((option) => option.value === normalized)
            || this.taskStatusOptions[0];
        },
        isTaskDoneStatus(status) {
          return String(status || "").trim() === "done";
        },
        isTaskCanceledStatus(status) {
          return String(status || "").trim() === "canceled";
        },
        isTaskActiveStatus(status) {
          const normalized = String(status || "").trim();
          return normalized === "todo" || normalized === "in_progress";
        },
        statusChipClass(item) {
          if (this.activeSection === "deals") {
            return "";
          }
          return this.statusClass(item.status);
        },
        isTopPriorityItem(item) {
          if (this.activeSection === "companies") {
            return this.companyHasActiveDeals(item.id);
          }
          return false;
        },
        getSortRank(item) {
          if (this.activeSection === "leads") {
            const statusCode = String(item.statusCode || "").toLowerCase();
            if (statusCode === "lost") return 1;
            if (statusCode === "converted") return 2;
            if (statusCode === "spam") return 3;
            return 0;
          }
          if (this.activeSection === "deals") {
            const palette = this.dealStatusCategory(item);
            if (palette === "won") return 1;
            if (palette === "lost") return 2;
            return 0;
          }
          if (this.activeSection === "tasks") {
            return this.isTaskActiveStatus(item.taskStatus) ? 0 : 1;
          }
          return 0;
        },
        compareActiveTasksByDueAt(leftItem, rightItem) {
          const leftDueAt = this.parseTaskDueTimestamp(leftItem?.dueAtRaw);
          const rightDueAt = this.parseTaskDueTimestamp(rightItem?.dueAtRaw);
          const leftOverdue = leftDueAt !== null && leftDueAt < Date.now();
          const rightOverdue = rightDueAt !== null && rightDueAt < Date.now();

          if (leftOverdue !== rightOverdue) {
            return leftOverdue ? -1 : 1;
          }
          if (leftDueAt === null && rightDueAt === null) {
            return 0;
          }
          if (leftDueAt === null) {
            return 1;
          }
          if (rightDueAt === null) {
            return -1;
          }
          return leftDueAt - rightDueAt;
        },
        parseTaskDueTimestamp(value) {
          if (!value) return null;
          const parsed = new Date(value);
          const timestamp = parsed.getTime();
          return Number.isNaN(timestamp) ? null : timestamp;
        },
        statusChipStyle(item) {
          if (this.activeSection !== "deals") {
            return null;
          }

          const palette = this.dealStatusPalette(item);
          return {
            borderColor: palette.border,
            backgroundColor: palette.bg,
            color: palette.text,
          };
        },
        dealStatusCategory(item) {
          const stage = this.metaOptions.dealStages.find(
            (candidate) => String(candidate.id) === String(item.stageId)
          );
          const token = `${stage?.code || ""} ${stage?.name || ""} ${item.stageName || ""}`.toLowerCase();

          if (item.isWon || /(won|success|успеш)/.test(token)) {
            return "won";
          }
          if (/(lost|failed|not_realized|не реализ|проигр|закрыт)/.test(token)) {
            return "lost";
          }
          if (/(contract|approval|договор|согласован)/.test(token)) {
            return "contract";
          }
          if (/(decision|решени)/.test(token)) {
            return "decision";
          }
          if (/(negoti|переговор)/.test(token)) {
            return "negotiation";
          }
          if (/(contact|new|open|первич|нов)/.test(token)) {
            return "new";
          }
          return "default";
        },
        dealStatusPalette(item) {
          const category = this.dealStatusCategory(item);

          if (category === "won") {
            return { border: "rgba(52, 211, 153, .35)", bg: "rgba(16, 185, 129, .12)", text: "#6ee7b7" };
          }
          if (category === "lost") {
            return { border: "rgba(248, 113, 113, .35)", bg: "rgba(239, 68, 68, .12)", text: "#fca5a5" };
          }
          if (category === "contract") {
            return { border: "rgba(129, 140, 248, .35)", bg: "rgba(99, 102, 241, .12)", text: "#c7d2fe" };
          }
          if (category === "decision") {
            return { border: "rgba(167, 139, 250, .35)", bg: "rgba(139, 92, 246, .12)", text: "#ddd6fe" };
          }
          if (category === "negotiation") {
            return { border: "rgba(56, 189, 248, .35)", bg: "rgba(14, 165, 233, .12)", text: "#bae6fd" };
          }
          if (category === "new") {
            return { border: "rgba(251, 191, 36, .35)", bg: "rgba(245, 158, 11, .12)", text: "#fde68a" };
          }

          const orderedStages = this.metaOptions.dealStages.filter(
            (stage) => stage && stage.is_active !== false && !stage.is_final
          );
          const stageIndex = orderedStages.findIndex(
            (stage) => String(stage.id) === String(item.stageId)
          );
          const stagePalette = [
            { border: "rgba(251, 191, 36, .35)", bg: "rgba(245, 158, 11, .12)", text: "#fde68a" },
            { border: "rgba(56, 189, 248, .35)", bg: "rgba(14, 165, 233, .12)", text: "#bae6fd" },
            { border: "rgba(129, 140, 248, .35)", bg: "rgba(99, 102, 241, .12)", text: "#c7d2fe" },
            { border: "rgba(167, 139, 250, .35)", bg: "rgba(139, 92, 246, .12)", text: "#ddd6fe" },
            { border: "rgba(244, 114, 182, .35)", bg: "rgba(236, 72, 153, .12)", text: "#f9a8d4" },
            { border: "rgba(45, 212, 191, .35)", bg: "rgba(20, 184, 166, .12)", text: "#99f6e4" },
          ];
          if (stageIndex >= 0) {
            return stagePalette[stageIndex % stagePalette.length];
          }

          return { border: "rgba(148, 163, 184, .35)", bg: "rgba(148, 163, 184, .10)", text: "#cbd5e1" };
        },
        toggleStatusFilter() {
          this.showStatusFilter = !this.showStatusFilter;
        },
        toggleStatusFilterValue(value) {
          if (this.selectedStatusFilters.includes(value)) {
            this.selectedStatusFilters = this.selectedStatusFilters.filter((item) => item !== value);
            return;
          }
          this.selectedStatusFilters = [...this.selectedStatusFilters, value];
        },
        clearStatusFilter() {
          this.selectedStatusFilters = [];
        },
        clearTaskDealFilter() {
          this.taskDealFilterId = null;
          this.taskDealFilterLabel = "";
        },
        companyHasActiveDeals(companyId) {
          const normalizedCompanyId = this.toIntOrNull(companyId);
          if (!normalizedCompanyId) return false;
          return this.datasets.deals.some((deal) => {
            if (String(deal.clientId || "") !== String(normalizedCompanyId)) {
              return false;
            }
            return this.getDealStatusBucket(deal) !== "done";
          });
        },
        countCompanyActiveDeals(companyId) {
          const normalizedCompanyId = this.toIntOrNull(companyId);
          if (!normalizedCompanyId) return 0;
          return this.datasets.deals.filter((deal) => {
            if (String(deal.clientId || "") !== String(normalizedCompanyId)) {
              return false;
            }
            return this.getDealStatusBucket(deal) !== "done";
          }).length;
        },
        countCompanyOpenTasks(companyId) {
          const normalizedCompanyId = this.toIntOrNull(companyId);
          if (!normalizedCompanyId) return 0;
          const dealIds = new Set(
            this.datasets.deals
              .filter((deal) => String(deal.clientId || "") === String(normalizedCompanyId))
              .map((deal) => String(deal.id))
          );
          const taskIds = new Set();
          this.datasets.tasks.forEach((task) => {
            if (!this.isTaskActiveStatus(task.taskStatus)) {
              return;
            }
            const matchesClient = String(task.clientId || "") === String(normalizedCompanyId);
            const matchesDeal = task.dealId && dealIds.has(String(task.dealId));
            if (matchesClient || matchesDeal) {
              taskIds.add(String(task.id));
            }
          });
          return taskIds.size;
        },
        countDealOpenTasks(dealId) {
          const normalizedDealId = this.toIntOrNull(dealId);
          if (!normalizedDealId) return 0;
          return this.datasets.tasks.filter((task) => {
            if (String(task.dealId || "") !== String(normalizedDealId)) {
              return false;
            }
            return this.isTaskActiveStatus(task.taskStatus);
          }).length;
        },
        getCurrencyRateToRub(currency) {
          const code = String(currency || "RUB").trim().toUpperCase() || "RUB";
          const rates = (this.metaOptions && this.metaOptions.currencyRates) || { RUB: 1 };
          const rate = Number(rates[code]);
          if (code === "RUB") return 1;
          return Number.isFinite(rate) && rate > 0 ? rate : 0;
        },
        convertAmountToRub(amount, currency) {
          const numericAmount = Number(amount || 0);
          if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
            return 0;
          }
          const safeCurrency = String(currency || "RUB").trim().toUpperCase() || "RUB";
          if (safeCurrency === "RUB") {
            return numericAmount;
          }
          return numericAmount * this.getCurrencyRateToRub(safeCurrency);
        },
        getItemAmountRub(item) {
          if (this.activeSection === "leads") {
            const numericValue = Number(item.expectedValue || 0);
            return Number.isFinite(numericValue) && numericValue > 0 ? numericValue : 0;
          }
          if (this.activeSection === "deals") {
            return this.convertAmountToRub(item.amount, item.currency);
          }
          return 0;
        },
        sumItemsAmountRub(items) {
          return (items || []).reduce((sum, item) => sum + this.getItemAmountRub(item), 0);
        },
        formatDealAmount(amount, currency) {
          const numericAmount = Number(amount || 0);
          const safeCurrency = String(currency || "RUB").trim() || "RUB";
          if (!Number.isFinite(numericAmount)) {
            return `0 ${safeCurrency}`;
          }
          return `${numericAmount.toLocaleString("ru-RU")} ${safeCurrency}`;
        },
        formatRubAmount(amount) {
          const numericAmount = Number(amount || 0);
          if (!Number.isFinite(numericAmount)) {
            return "0 RUB";
          }
          return `${Math.round(numericAmount).toLocaleString("ru-RU")} RUB`;
        },
        toggleCompanyCardDetails(companyId) {
          const key = String(companyId || "");
          if (!key) return;
          this.expandedCompanyCards = {
            ...this.expandedCompanyCards,
            [key]: !this.expandedCompanyCards[key],
          };
        },
        isCompanyCardExpanded(companyId) {
          return !!this.expandedCompanyCards[String(companyId || "")];
        },
        async handleGlobalKeydown(event) {
          if (!this.showModal) return;

          if (event.key === "Escape") {
            event.preventDefault();
            this.closeModal();
            return;
          }

          if (event.key !== "Enter" || event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) {
            return;
          }

          const target = event.target;
          const tagName = String((target && target.tagName) || "").toUpperCase();
          if (tagName === "TEXTAREA") {
            return;
          }

          event.preventDefault();
          if (this.showFieldEditToggle && !this.isFieldEditModeActive()) {
            this.toggleFieldEditMode();
            return;
          }
          if (this.isSaving) {
            return;
          }
          await this.createItem();
        },
        handleDocumentClick(event) {
          if (!this.showStatusFilter) return;
          const target = event.target;
          if (target && target.closest && target.closest("[data-status-filter]")) return;
          this.showStatusFilter = false;
        },
        getStatusBucket(status) {
          if (["converted", "archived", "done", "lost", "unqualified", "spam"].includes(status)) {
            return "done";
          }
          if (["in_progress", "qualified", "attempting_contact", "progress"].includes(status)) {
            return "progress";
          }
          return "new";
        },
        getDealStatusBucket(item) {
          if (!item) return "new";
          const stageCode = String(item.stageCode || "").toLowerCase();
          if (item.isWon || item.status === "done" || stageCode === "won") {
            return "done";
          }
          if (stageCode === "primary_contact") {
            return "new";
          }
          return "progress";
        },
        getItemStatusBucket(item) {
          if (this.activeSection === "deals") {
            return this.getDealStatusBucket(item);
          }
          return this.getStatusBucket(item.status);
        },
        resolveLeadStatusLabel(code, fallback) {
          if (fallback) return fallback;
          return LEAD_STATUS_LABELS[code] || "Новый";
        },
        canQuickChangeLeadStatus(item) {
          if (this.activeSection !== "leads") return false;
          const nextCode = LEAD_STATUS_MAIN_FLOW_NEXT[item.statusCode];
          if (!nextCode) return false;
          return this.metaOptions.leadStatuses.some((status) => status.code === nextCode);
        },
        canQuickChangeStatus(item) {
          if (this.activeSection === "leads") {
            return this.canQuickChangeLeadStatus(item);
          }
          if (this.activeSection === "tasks") {
            return item.taskStatus === "todo" || item.taskStatus === "in_progress";
          }
          return false;
        },
        nextTaskStatus(currentStatus) {
          if (currentStatus === "todo") return "in_progress";
          if (currentStatus === "in_progress") return "done";
          return null;
        },
        getLeadStatusByCode(code) {
          return this.metaOptions.leadStatuses.find((status) => status.code === code) || null;
        },
        async setLeadStatus(leadId, targetCode) {
          const targetStatus = this.getLeadStatusByCode(targetCode);
          if (!targetStatus) {
            throw new Error(`Статус ${targetCode} не найден в справочнике`);
          }
          await this.apiRequest(`/api/v1/leads/${leadId}/`, {
            method: "PATCH",
            body: { status: targetStatus.id }
          });
        },
        async onStatusChipClick(item) {
          if (!this.canQuickChangeStatus(item)) return;
          try {
            this.isLoading = true;
            if (this.activeSection === "leads") {
              const targetCode = LEAD_STATUS_MAIN_FLOW_NEXT[item.statusCode];
              await this.setLeadStatus(item.id, targetCode);
              if (targetCode === "converted") {
                await Promise.all([this.loadSection("leads"), this.loadSection("deals")]);
              } else {
                await this.loadSection("leads");
              }
            }
            if (this.activeSection === "tasks") {
              const targetStatus = this.nextTaskStatus(item.taskStatus);
              if (targetStatus) {
                if (targetStatus === "done") {
                  this.openTaskEditor({ ...item, status: "done" });
                } else {
                  await this.apiRequest(`/api/v1/activities/${item.id}/`, {
                    method: "PATCH",
                    body: { status: targetStatus }
                  });
                  await this.loadSection("tasks");
                }
              }
            }
          } catch (error) {
            this.errorMessage = `Ошибка смены статуса: ${error.message}`;
          } finally {
            this.isLoading = false;
          }
        },
        onRowClick(item) {
          if (this.activeSection === "leads") {
            this.openLeadEditor(item);
            return;
          }
          if (this.activeSection === "deals") {
            this.openDealEditor(item);
            return;
          }
          if (this.activeSection === "contacts") {
            this.openContactEditor(item);
            return;
          }
          if (this.activeSection === "companies") {
            this.openCompanyEditor(item);
            return;
          }
          if (this.activeSection === "tasks") {
            this.openTaskEditor(item);
            return;
          }
          if (this.activeSection === "touches") {
            this.openTouchEditor(item);
          }
        },
        openLeadEditor(item) {
          this.clearUiErrors({ modalOnly: true });
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingDealId = null;
          this.showAllLeadFields = false;
          this.editingLeadId = item.id;
          this.forms.leads = {
            title: item.title || "",
            description: item.description || "",
            name: item.contactName || "",
            company: item.company || "",
            phone: item.phone || "",
            email: item.email || "",
            assignedToId: this.toIntOrNull(item.assignedToId),
            priority: item.priority || "medium",
            expectedValue: item.expectedValue || "",
            statusId: item.statusId || "",
            sourceId: item.sourceId || "",
            sourceName: item.sourceName || "",
            sourceCode: item.sourceCode || "",
            sourceNames: Array.isArray(item.sourceNames) ? item.sourceNames : [],
            history: Array.isArray(item.history) ? item.history : [],
            websiteSessionId: item.websiteSessionId || ""
          };
          this.showModal = true;
        },
        openDealEditor(item) {
          this.clearUiErrors({ modalOnly: true });
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingLeadId = null;
          this.showAllDealFields = false;
          this.editingDealId = item.id;
          this.forms.deals = {
            title: item.title || "",
            description: item.description || "",
            sourceId: item.sourceId || "",
            companyId: this.toIntOrNull(item.clientId),
            ownerId: this.toIntOrNull(item.ownerId),
            amount: item.amount ?? "0",
            closeDate: item.closeDate || "",
            stageId: item.stageId || "",
            failureReason: item.failureReason || "",
            events: item.events || ""
          };
          this.resetDealTaskForm();
          this.resetTaskFollowUpForm();
          this.showDealTaskForm = false;
          this.resetDealCompanyForm();
          this.showDealCompanyForm = false;
          this.showDealContactsPanel = false;
          this.showDealContactForm = false;
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          this.loadTasksForDeal();
          this.showModal = true;
        },
        openContactEditor(item) {
          this.clearUiErrors({ modalOnly: true });
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingContactId = item.id;
          this.forms.contacts = {
            fullName: item.fullName || item.name || "",
            companyId: this.toIntOrNull(item.clientId),
            position: item.position || "",
            phone: item.phone || "",
            email: item.email || "",
            isPrimary: !!item.isPrimary
          };
          this.showModal = true;
        },
        openCompanyEditor(item) {
          this.clearUiErrors({ modalOnly: true });
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingCompanyId = item.id;
          this.showCompanyEvents = false;
          this.showCompanyNoteDraft = false;
          this.showAllCompanyFields = false;
          const normalizedOkveds = this.normalizeCompanyOkveds(item.okveds, item.okved, item.industry);
          const resolvedIndustry = this.resolvePrimaryIndustry(item.industry, item.okved, normalizedOkveds);
          this.forms.companies = {
            name: item.name || "",
            legalName: item.legalName || "",
            inn: item.inn || "",
            address: item.address || "",
            industry: resolvedIndustry,
            okved: item.okved || "",
            okveds: normalizedOkveds,
            phone: item.phone || "",
            email: item.email || "",
            currency: item.currency || "RUB",
            website: item.website || "",
            workRules: this.normalizeCompanyWorkRules(item.workRules),
            notes: item.notes || "",
            noteDraft: "",
            events: item.events || "",
            isActive: item.isActive !== false
          };
          this.showCompanyOkvedDetails = false;
          this.resetCompanyContactForm();
          this.showCompanyContactForm = false;
          this.loadContactsForCompany();
          this.showModal = true;
          this.enrichCompanyFromDadataByInn();
        },
        openTaskEditor(item) {
          this.clearUiErrors({ modalOnly: true });
          this.activeSection = "tasks";
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.showAllTaskFields = false;
          this.editingTaskId = item.id;
          this.forms.tasks = {
            subject: item.subject || item.name || "",
            taskTypeId: this.toIntOrNull(item.taskTypeId),
            priority: item.priority || "medium",
            companyId: this.toIntOrNull(item.clientId),
            dealId: this.toIntOrNull(item.dealId),
            relatedTouchId: this.toIntOrNull(item.relatedTouchId),
            dueAt: this.toDateTimeLocal(item.dueAtRaw),
            reminderOffsetMinutes: Number(item.reminderOffsetMinutes || 30),
            description: item.description || "",
            result: item.result || "",
            saveCompanyNote: !!item.saveCompanyNote,
            companyNote: item.companyNote || "",
            status: item.taskStatus || item.status || "todo"
          };
          this.resetTaskFollowUpForm();
          this.showModal = true;
          this.loadTaskTouchOptions();
        },
        openTouchEditor(item) {
          this.clearUiErrors({ modalOnly: true });
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingTouchId = item.id;
          this.forms.touches = {
            happenedAt: this.toDateTimeLocal(item.happenedAtRaw),
            channelId: this.toIntOrNull(item.channelId),
            direction: item.direction || "outgoing",
            result: item.result || "",
            summary: item.summary || "",
            nextStep: item.nextStep || "",
            nextStepAt: this.toDateTimeLocal(item.nextStepAtRaw),
            ownerId: this.toIntOrNull(item.ownerId),
            companyId: this.toIntOrNull(item.clientId),
            contactId: this.toIntOrNull(item.contactId),
            taskId: this.toIntOrNull(item.taskId),
            leadId: this.toIntOrNull(item.leadId),
            dealId: this.toIntOrNull(item.dealId),
          };
          this.showModal = true;
        },
        openTaskFromDeal(task) {
          this.taskDealFilterId = task.dealId || this.editingDealId || null;
          this.taskDealFilterLabel = task.deal || this.forms.deals.title || "";
          this.openTaskEditor(task);
        },
        async openTaskListForDeal() {
          if (!this.editingDealId) return;
          this.taskDealFilterId = this.editingDealId;
          this.taskDealFilterLabel = this.forms.deals.title || `Сделка #${this.editingDealId}`;
          this.closeModal();
          this.activeSection = "tasks";
          this.search = "";
          this.showStatusFilter = false;
          this.selectedStatusFilters = [];
          if (!this.datasets.tasks.length) {
            await this.reloadActiveSection();
          }
        },
        toggleDealTaskForm() {
          this.showDealTaskForm = !this.showDealTaskForm;
        },
        handleDealCompanySelectChange() {
          if (this.forms.deals.companyId !== "__create__") {
            this.showDealCompanyForm = false;
            this.showDealContactsPanel = false;
            this.showDealContactForm = false;
            this.dealCompanyContacts = [];
            this.resetDealCompanyForm();
            return;
          }
          this.forms.deals.companyId = null;
          this.resetDealCompanyForm();
          this.showDealCompanyForm = true;
          this.showDealContactsPanel = false;
          this.showDealContactForm = false;
          this.dealCompanyContacts = [];
        },
        cancelDealCompanyCreation() {
          this.forms.deals.companyId = null;
          this.showDealCompanyForm = false;
          this.resetDealCompanyForm();
        },
        async toggleDealContactsPanel() {
          if (!this.dealHasSelectedCompany) return;
          this.showDealContactsPanel = !this.showDealContactsPanel;
          if (this.showDealContactsPanel) {
            await this.loadContactsForSelectedDealCompany();
            return;
          }
          this.showDealContactForm = false;
        },
        toggleDealContactForm() {
          if (!this.dealHasSelectedCompany) return;
          this.showDealContactForm = !this.showDealContactForm;
          if (!this.showDealContactForm) {
            this.resetDealCompanyContactForm();
          }
        },
        resetDealTaskForm() {
          this.dealTaskForm = {
            subject: "",
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          };
        },
        resetTaskFollowUpForm() {
          this.taskFollowUpForm = {
            subject: "",
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          };
        },
        hasPendingDealTaskDraft() {
          return !!(
            this.dealTaskForm.subject.trim()
            || this.dealTaskForm.dueAt
            || this.dealTaskForm.description.trim()
          );
        },
        isDealStageAllowedWithoutTasks(stageId) {
          const stage = this.metaOptions.dealStages.find(
            (candidate) => String(candidate.id) === String(stageId)
          );
          const stageCode = String((stage && stage.code) || "").trim().toLowerCase();
          return ["won", "failed"].includes(stageCode);
        },
        isDealStageRequiringCompany(stageId) {
          const stage = this.metaOptions.dealStages.find(
            (candidate) => String(candidate.id) === String(stageId)
          );
          const stageCode = String((stage && stage.code) || "").trim().toLowerCase();
          const stageName = String((stage && stage.name) || "").trim().toLowerCase();
          return stageCode === "thinking" || stageName === "думают";
        },
        validateDealCompanyRequirement() {
          if (!this.isDealStageRequiringCompany(this.forms.deals.stageId)) {
            return;
          }
          if (this.toIntOrNull(this.forms.deals.companyId)) {
            return;
          }
          throw new Error("Для этапа «Думают» компания обязательна");
        },
        validateDealTaskRequirement() {
          if (this.isDealStageAllowedWithoutTasks(this.forms.deals.stageId)) {
            return;
          }
          const hasExistingActiveTasks = Array.isArray(this.dealTasksForActiveDeal)
            && this.dealTasksForActiveDeal.some((task) => this.isTaskActiveStatus(task.taskStatus));
          if (hasExistingActiveTasks || this.hasPendingDealTaskDraft()) {
            return;
          }
          throw new Error("Сделка без активных задач допустима только в статусах «Успешно» и «Провален»");
        },
        validateDealFailureReason() {
          if (!this.isDealFailedStageSelected) {
            return;
          }
          if (!String(this.forms.deals.failureReason || "").trim()) {
            throw new Error("Укажите причину провала сделки");
          }
        },
        validatePendingDealTaskDraft() {
          if (!this.hasPendingDealTaskDraft()) {
            return;
          }
          if (!this.dealTaskForm.subject.trim()) {
            throw new Error("Укажите название новой задачи по сделке");
          }
          if (!this.dealTaskForm.dueAt) {
            throw new Error("Укажите срок новой задачи по сделке");
          }
        },
        hasPreparedTaskFollowUp() {
          return !!(
            this.taskFollowUpForm.subject.trim()
            && this.taskFollowUpForm.dueAt
          );
        },
        validateTaskFollowUpRequirement() {
          if (!this.isTaskDoneStatus(this.forms.tasks.status) || !this.taskActiveDealRequiresFollowUp) {
            return;
          }
          const hasOtherActiveTasks = Array.isArray(this.datasets.tasks)
            && this.datasets.tasks.some((task) => (
              String(task.id) !== String(this.editingTaskId)
              && String(task.dealId || "") === String(this.toIntOrNull(this.forms.tasks.dealId) || "")
              && this.isTaskActiveStatus(task.taskStatus)
            ));
          if (hasOtherActiveTasks || this.hasPreparedTaskFollowUp()) {
            return;
          }
          throw new Error("Для активной сделки заполните следующую задачу перед завершением текущей");
        },
        resetDealCompanyForm() {
          this.dealCompanyForm = {
            name: "",
            inn: "",
            address: "",
            industry: "",
            okved: "",
            phone: "",
            email: "",
            currency: "RUB",
            website: ""
          };
          this.resetDealCompanyContactForm();
        },
        resetDealCompanyContactForm() {
          this.dealCompanyContactForm = {
            fullName: "",
            position: "",
            phone: "",
            email: "",
            isPrimary: true
          };
        },
        formatDueLabel(value) {
          if (!value) return "не указан";
          const date = new Date(value);
          if (Number.isNaN(date.getTime())) return "не указан";
          return date.toLocaleString("ru-RU", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          });
        },
        formatRemainingDuration(totalMinutes) {
          const minutes = Math.max(1, Math.ceil(Number(totalMinutes) || 0));
          if (minutes < 60) {
            return `${minutes} мин`;
          }

          const hours = Math.floor(minutes / 60);
          const restMinutes = minutes % 60;
          if (hours < 24) {
            return restMinutes ? `${hours} ч ${restMinutes} мин` : `${hours} ч`;
          }

          const days = Math.floor(hours / 24);
          const restHours = hours % 24;
          const chunks = [`${days} д`];
          if (restHours) chunks.push(`${restHours} ч`);
          if (restMinutes) chunks.push(`${restMinutes} мин`);
          return chunks.join(" ");
        },
        formatTaskRemainingLabel(value, status = "todo") {
          if (!value) return "";
          if (this.isTaskDoneStatus(status)) return "Задача выполнена";
          if (this.isTaskCanceledStatus(status)) return "Задача отменена";

          const date = new Date(value);
          if (Number.isNaN(date.getTime())) return "";

          const diffMinutes = Math.ceil((date.getTime() - Date.now()) / 60000);
          const absoluteLabel = this.formatRemainingDuration(Math.abs(diffMinutes));
          if (diffMinutes >= 0) {
            return `Осталось ${absoluteLabel}`;
          }
          return `Просрочено на ${absoluteLabel}`;
        },
        parseDealCloseDate(value) {
          if (!value) return null;
          const normalized = String(value).trim();
          const match = normalized.match(/^(\d{4})-(\d{2})-(\d{2})$/);
          if (match) {
            const year = Number(match[1]);
            const month = Number(match[2]) - 1;
            const day = Number(match[3]);
            return new Date(year, month, day, 23, 59, 59, 999);
          }
          const parsed = new Date(normalized);
          return Number.isNaN(parsed.getTime()) ? null : parsed;
        },
        formatDealCloseDate(value) {
          if (!value) return "";
          const parsed = this.parseDealCloseDate(value);
          if (!parsed) return String(value || "");
          return parsed.toLocaleDateString("ru-RU");
        },
        isDealOverdue(value) {
          const parsed = this.parseDealCloseDate(value);
          if (!parsed) return false;
          return parsed.getTime() < Date.now();
        },
        dealClosePrimaryLabel(value) {
          if (!value) return "";
          return this.isDealOverdue(value) ? "Просрочено" : this.formatDealCloseDate(value);
        },
        dealCloseSecondaryLabel(value) {
          if (!value) return "";
          if (!this.isDealOverdue(value)) return "";
          const parsed = this.parseDealCloseDate(value);
          if (!parsed) return "";
          const diffMinutes = Math.ceil((Date.now() - parsed.getTime()) / 60000);
          return this.formatRemainingDuration(diffMinutes);
        },
        isTaskOverdue(value, status = "todo") {
          if (!value || !this.isTaskActiveStatus(status)) return false;
          const parsed = new Date(value);
          if (Number.isNaN(parsed.getTime())) return false;
          return parsed.getTime() < Date.now();
        },
        taskDuePrimaryLabel(value, status = "todo") {
          if (!value) return "";
          return this.isTaskOverdue(value, status) ? "Просрочено" : this.formatDueLabel(value);
        },
        taskDueSecondaryLabel(value, status = "todo") {
          if (!value) return "";
          if (this.isTaskOverdue(value, status)) {
            const parsed = new Date(value);
            if (Number.isNaN(parsed.getTime())) return "";
            const diffMinutes = Math.ceil((Date.now() - parsed.getTime()) / 60000);
            return this.formatRemainingDuration(diffMinutes);
          }
          return this.formatTaskRemainingLabel(value, status);
        },
        normalizeCompanyOkveds(okveds, mainCode = "", mainName = "") {
          const normalized = [];
          if (Array.isArray(okveds)) {
            for (const entry of okveds) {
              if (!entry || typeof entry !== "object") continue;
              const code = String(entry.code || entry.okved || "").trim();
              const name = String(entry.name || entry.title || "").trim();
              if (!code && !name) continue;
              normalized.push({
                code,
                name,
                main: !!entry.main,
              });
            }
          }
          const mainCodeText = String(mainCode || "").trim();
          const mainNameText = String(mainName || "").trim();
          if (mainCodeText && !normalized.some((entry) => entry.code === mainCodeText)) {
            normalized.unshift({ code: mainCodeText, name: mainNameText, main: true });
          }
          if (!normalized.length && (mainCodeText || mainNameText)) {
            normalized.push({ code: mainCodeText, name: mainNameText, main: true });
          }
          return normalized;
        },
        isSyntheticIndustry(industryText, okvedCode = "") {
          const industry = String(industryText || "").trim().toLowerCase();
          const code = String(okvedCode || "").trim().toLowerCase();
          if (!industry || !code) return false;
          const normalized = industry.replace(/\s+/g, " ");
          return normalized === `оквэд ${code}` || normalized === `оквэд: ${code}`;
        },
        resolvePrimaryIndustry(industryText, okvedCode = "", okvedEntries = []) {
          const industry = String(industryText || "").trim();
          const code = String(okvedCode || "").trim();
          const entries = Array.isArray(okvedEntries) ? okvedEntries : [];
          const mainEntry = entries.find((entry) => entry && entry.main) || entries[0] || null;
          const decoded = mainEntry ? String(mainEntry.name || "").trim() : "";
          if (decoded && (!industry || this.isSyntheticIndustry(industry, code))) {
            return decoded;
          }
          return industry;
        },
        primaryCompanyOkvedEntry() {
          const entries = Array.isArray(this.forms.companies.okveds) ? this.forms.companies.okveds : [];
          const explicitMain = entries.find((entry) => entry && entry.main);
          if (explicitMain) return explicitMain;
          if (entries.length) return entries[0];
          return {
            code: this.forms.companies.okved || "",
            name: this.forms.companies.industry || "",
            main: true,
          };
        },
        secondaryCompanyOkvedEntries() {
          const entries = Array.isArray(this.forms.companies.okveds) ? this.forms.companies.okveds : [];
          if (!entries.length) return [];
          const primary = this.primaryCompanyOkvedEntry();
          return entries.filter((entry, index) => {
            if (!entry) return false;
            if (index === 0 && !primary.main) return true;
            return !(entry.code === primary.code && entry.name === primary.name);
          });
        },
        toggleCompanyOkvedDetails() {
          if (!this.secondaryCompanyOkvedEntries().length) {
            this.showCompanyOkvedDetails = false;
            return;
          }
          this.showCompanyOkvedDetails = !this.showCompanyOkvedDetails;
        },
        async enrichCompanyFromDadataByInn() {
          const inn = String(this.forms.companies.inn || "").trim();
          if (inn.length < 10) {
            return;
          }
          const hasDetailedOkveds = this.normalizeCompanyOkveds(
            this.forms.companies.okveds,
            this.forms.companies.okved,
            this.forms.companies.industry
          ).length > 1;
          const hasReadableIndustry = !!String(this.forms.companies.industry || "").trim() && !this.isSyntheticIndustry(
            this.forms.companies.industry,
            this.forms.companies.okved
          );
          if (hasDetailedOkveds && hasReadableIndustry) {
            return;
          }
          try {
            const payload = await this.apiRequest(`/api/dadata/party/by-inn/?inn=${encodeURIComponent(inn)}`);
            const profile = payload && payload.profile ? payload.profile : null;
            if (!profile) {
              return;
            }
            const okveds = this.normalizeCompanyOkveds(profile.okveds, profile.okved, profile.industry);
            const resolvedIndustry = this.resolvePrimaryIndustry(profile.industry, profile.okved, okveds);
            if (profile.okved) {
              this.forms.companies.okved = profile.okved;
            }
            if (resolvedIndustry) {
              this.forms.companies.industry = resolvedIndustry;
            }
            if (okveds.length) {
              this.forms.companies.okveds = okveds;
            }
          } catch (error) {
            // silent fallback: keep existing company data
          }
        },
        async loadTasksForDeal() {
          if (!this.editingDealId) {
            this.dealTasksForActiveDeal = [];
            return;
          }
          this.isDealTasksLoading = true;
          try {
            const payload = await this.apiRequest(
              `/api/v1/activities/?type=task&deal=${this.editingDealId}&page_size=100`
            );
            const tasks = this.normalizePaginatedResponse(payload);
            this.dealTasksForActiveDeal = tasks.map((item) => {
              const taskStatus = item.status || (item.is_done ? "done" : "todo");
              return {
              id: item.id,
              subject: item.subject || `Задача #${item.id}`,
              description: item.description || "",
              result: item.result || "",
              saveCompanyNote: !!item.save_company_note,
              companyNote: item.company_note || "",
              company: item.client_name || "",
              clientId: item.client || null,
              deal: item.deal_title || this.forms.deals.title || "",
              dealId: item.deal || this.editingDealId || null,
              dueAtRaw: item.due_at || null,
              taskStatus,
              statusLabel: this.taskStatusMeta(taskStatus).label,
              dueLabel: this.formatDueLabel(item.due_at),
              remainingLabel: this.formatTaskRemainingLabel(item.due_at, taskStatus),
            };
            });
          } catch (error) {
            this.errorMessage = `Ошибка загрузки задач сделки: ${error.message}`;
            this.dealTasksForActiveDeal = [];
          } finally {
            this.isDealTasksLoading = false;
          }
        },
        async loadTaskTouchOptions() {
          const dealId = this.toIntOrNull(this.forms.tasks.dealId);
          const clientId = this.toIntOrNull(this.forms.tasks.companyId);
          if (!dealId && !clientId) {
            this.taskTouchOptions = [];
            return;
          }

          const params = new URLSearchParams({ page_size: "100", exclude_type: "task" });
          if (dealId) params.set("deal", String(dealId));
          if (clientId) params.set("client", String(clientId));

          this.isTaskTouchesLoading = true;
          try {
            const payload = await this.apiRequest(`/api/v1/activities/?${params.toString()}`);
            const touches = this.normalizePaginatedResponse(payload);
            this.taskTouchOptions = touches.map((item) => ({
              id: item.id,
              subject: item.subject || `Активность #${item.id}`,
              type: item.type || "",
              label: `${item.subject || `Активность #${item.id}`} · ${this.humanizeActivityType(item.type)}`,
            }));
          } catch (error) {
            this.taskTouchOptions = [];
            this.setUiError(`Ошибка загрузки связанных касаний: ${error.message}`, { modal: true });
          } finally {
            this.isTaskTouchesLoading = false;
          }
        },
        async loadContactsForSelectedDealCompany() {
          const companyId = this.toIntOrNull(this.forms.deals.companyId);
          if (!companyId) {
            this.dealCompanyContacts = [];
            return;
          }
          this.isDealContactsLoading = true;
          try {
            const payload = await this.apiRequest(`/api/v1/contacts/?client=${companyId}&page_size=100`);
            const contacts = this.normalizePaginatedResponse(payload);
            this.dealCompanyContacts = contacts.map((item) => ({
              id: item.id,
              fullName: `${item.first_name || ""} ${item.last_name || ""}`.trim() || `Контакт #${item.id}`,
              position: item.position || "",
              phone: item.phone || "",
              email: item.email || "",
              isPrimary: !!item.is_primary,
              clientId: item.client || companyId
            }));
          } catch (error) {
            this.errorMessage = `Ошибка загрузки контактов компании: ${error.message}`;
            this.dealCompanyContacts = [];
          } finally {
            this.isDealContactsLoading = false;
          }
        },
        openContactFromDealCompany(contact) {
          this.openContactEditor({
            id: contact.id,
            fullName: contact.fullName || "",
            clientId: contact.clientId || this.toIntOrNull(this.forms.deals.companyId),
            position: contact.position || "",
            phone: contact.phone || "",
            email: contact.email || "",
            isPrimary: !!contact.isPrimary
          });
        },
        toggleCompanyContactForm() {
          this.showCompanyContactForm = !this.showCompanyContactForm;
        },
        resetCompanyContactForm() {
          this.companyContactForm = {
            fullName: "",
            position: "",
            phone: "",
            email: "",
            isPrimary: false
          };
        },
        async loadContactsForCompany() {
          if (!this.editingCompanyId) {
            this.companyContactsForActiveCompany = [];
            return;
          }
          this.isCompanyContactsLoading = true;
          try {
            const payload = await this.apiRequest(
              `/api/v1/contacts/?client=${this.editingCompanyId}&page_size=100`
            );
            const contacts = this.normalizePaginatedResponse(payload);
            this.companyContactsForActiveCompany = contacts.map((item) => ({
              id: item.id,
              fullName: `${item.first_name || ""} ${item.last_name || ""}`.trim() || `Контакт #${item.id}`,
              position: item.position || "",
              phone: item.phone || "",
              email: item.email || "",
              isPrimary: !!item.is_primary,
              clientId: item.client || null
            }));
          } catch (error) {
            this.errorMessage = `Ошибка загрузки контактов компании: ${error.message}`;
            this.companyContactsForActiveCompany = [];
          } finally {
            this.isCompanyContactsLoading = false;
          }
        },
        openContactFromCompany(contact) {
          this.activeSection = "contacts";
          this.showStatusFilter = false;
          this.selectedStatusFilters = [];
          this.openContactEditor({
            id: contact.id,
            fullName: contact.fullName || "",
            clientId: contact.clientId || this.editingCompanyId,
            position: contact.position || "",
            phone: contact.phone || "",
            email: contact.email || "",
            isPrimary: !!contact.isPrimary
          });
        },
        mapLead(item) {
          const statusCode = item.status_code || "new";
          const label = this.resolveLeadStatusLabel(statusCode, item.status_name);
          return {
            id: item.id,
            name: item.title || item.name || `Лид #${item.id}`,
            description: item.description || "",
            company: item.client_name || item.company || "",
            phone: item.phone || "",
            email: item.email || "",
            assignedToId: item.assigned_to || null,
            assignedToName: item.assigned_to_name || "",
            status: statusCode,
            statusCode,
            statusId: item.status || "",
            sourceId: item.source || "",
            sourceName: item.source_name || "",
            sourceCode: item.source_code || "",
            statusLabel: label,
            title: item.title || "",
            contactName: item.name || "",
            priority: item.priority || "medium",
            expectedValue: item.expected_value || "",
            sourceNames: Array.isArray(item.source_names) ? item.source_names : [],
            history: Array.isArray(item.history) ? item.history : [],
            websiteSessionId: item.website_session_id || ""
          };
        },
        mapDeal(item) {
          const stage = this.metaOptions.dealStages.find(
            (candidate) => String(candidate.id) === String(item.stage)
          );
          const stageCode = String((stage && stage.code) || "").toLowerCase();
          const stageName = String(item.stage_name || "").toLowerCase();
          let normalized = this.uiStatus("progress", item.stage_name || "В работе");
          if (item.is_won || item.closed_at || stageCode === "won") {
            const doneLabel = item.is_won
              ? "Выиграна"
              : (stageCode === "won" ? (item.stage_name || "Won") : "Закрыта");
            normalized = this.uiStatus("done", doneLabel);
          } else if (
            stageCode === "primary_contact" ||
            stageName.includes("первич") ||
            stageName.includes("нов")
          ) {
            normalized = this.uiStatus("new", item.stage_name);
          }
          return {
            id: item.id,
            name: item.title || `Сделка #${item.id}`,
            description: item.description || "",
            sourceId: item.source || "",
            sourceName: item.source_name || "",
            company: item.client_name || "",
            phone: "",
            email: "",
            status: normalized.status,
            statusLabel: normalized.label,
            title: item.title || "",
            clientId: item.client || null,
            ownerId: item.owner || null,
            ownerName: item.owner_name || "",
            stageId: item.stage || "",
            stageCode,
            stageName: item.stage_name || "",
            amount: item.amount ?? 0,
            currency: item.currency || "RUB",
            closeDate: item.close_date || "",
            failureReason: item.failure_reason || "",
            events: item.events || "",
            isWon: !!item.is_won
          };
        },
        mapContact(item) {
          const fullName = `${item.first_name || ""} ${item.last_name || ""}`.trim();
          const normalized = this.uiStatus(item.is_primary ? "done" : "progress", item.is_primary ? "Основной" : "Активный");
          return {
            id: item.id,
            name: fullName || `Контакт #${item.id}`,
            fullName: fullName || `Контакт #${item.id}`,
            company: item.client_name || "",
            phone: item.phone || "",
            email: item.email || "",
            status: normalized.status,
            statusLabel: normalized.label,
            clientId: item.client || null,
            firstName: item.first_name || "",
            lastName: item.last_name || "",
            position: item.position || "",
            isPrimary: !!item.is_primary
          };
        },
        mapClient(item) {
          const normalized = this.uiStatus(item.is_active ? "progress" : "done", item.is_active ? "Активный" : "Неактивный");
          const normalizedOkveds = this.normalizeCompanyOkveds(item.okveds, item.okved, item.industry);
          const primaryOkved = normalizedOkveds.find((entry) => entry.main) || normalizedOkveds[0] || { code: "", name: "" };
          const resolvedIndustry = this.resolvePrimaryIndustry(item.industry, item.okved, normalizedOkveds);
          return {
            id: item.id,
            name: item.name || `Компания #${item.id}`,
            company: item.name || "",
            phone: item.phone || "",
            email: item.email || "",
            status: normalized.status,
            statusLabel: normalized.label,
            legalName: item.legal_name || "",
            inn: item.inn || "",
            address: item.address || "",
            industry: resolvedIndustry || primaryOkved.name || "",
            okved: item.okved || primaryOkved.code || "",
            okveds: normalizedOkveds,
            website: item.website || "",
            workRules: this.normalizeCompanyWorkRules(item.work_rules),
            notes: item.notes || "",
            events: item.events || "",
            currency: item.currency || "RUB",
            isActive: item.is_active !== false
          };
        },
        mapTask(item) {
          const taskStatus = item.status || (item.is_done ? "done" : "todo");
          const statusMeta = this.taskStatusMeta(taskStatus);
          const normalized = this.uiStatus(
            this.isTaskActiveStatus(taskStatus) ? "progress" : "done",
            statusMeta.label
          );
          return {
            id: item.id,
            name: item.subject || `Задача #${item.id}`,
            subject: item.subject || `Задача #${item.id}`,
            description: item.description || "",
            result: item.result || "",
            saveCompanyNote: !!item.save_company_note,
            companyNote: item.company_note || "",
            taskTypeId: item.task_type || null,
            taskTypeName: item.task_type_name || "",
            priority: item.priority || "medium",
            reminderOffsetMinutes: Number(item.deadline_reminder_offset_minutes || 30),
            company: item.client_name || "",
            clientId: item.client || null,
            deal: item.deal_title || "",
            dealId: item.deal || null,
            dueLabel: this.formatDueLabel(item.due_at),
            remainingLabel: this.formatTaskRemainingLabel(item.due_at, taskStatus),
            dueAtRaw: item.due_at || null,
            isDone: !!item.is_done,
            taskStatus,
            relatedTouchId: item.related_touch || null,
            relatedTouchSubject: item.related_touch_subject || "",
            phone: "",
            email: "",
            status: normalized.status,
            statusLabel: normalized.label
          };
        },
        mapTouch(item) {
          const direction = item.direction || "outgoing";
          const directionLabel = item.direction_label || (direction === "incoming" ? "Входящее" : "Исходящее");
          const normalized = this.uiStatus(direction === "incoming" ? "new" : "progress", directionLabel);
          return {
            id: item.id,
            name: item.summary || item.result || `Касание #${item.id}`,
            summary: item.summary || "",
            result: item.result || "",
            company: item.company_name || "",
            phone: item.task_subject
              ? `Задача: ${item.task_subject}`
              : (item.deal_title
                ? `Сделка: ${item.deal_title}`
                : (item.lead_title
                  ? `Лид: ${item.lead_title}`
                  : (item.contact_name ? `Контакт: ${item.contact_name}` : "—"))),
            email: this.formatDueLabel(item.happened_at),
            status: normalized.status,
            statusLabel: normalized.label,
            happenedAtRaw: item.happened_at || null,
            channelId: item.channel || null,
            channelName: item.channel_name || "",
            direction,
            nextStep: item.next_step || "",
            nextStepAtRaw: item.next_step_at || null,
            ownerId: item.owner || null,
            ownerName: item.owner_name || "",
            clientId: item.client || null,
            contactId: item.contact || null,
            contactName: item.contact_name || "",
            taskId: item.task || null,
            taskSubject: item.task_subject || "",
            leadId: item.lead || null,
            leadTitle: item.lead_title || "",
            dealId: item.deal || null,
            dealTitle: item.deal_title || "",
          };
        },
        async loadSection(section) {
          const endpoint = SECTION_ENDPOINTS[section];
          if (!endpoint) return;
          const payload = await this.apiRequest(endpoint);
          const records = this.normalizePaginatedResponse(payload);
          if (section === "leads") this.datasets.leads = records.map(this.mapLead);
          if (section === "deals") this.datasets.deals = records.map(this.mapDeal);
          if (section === "contacts") this.datasets.contacts = records.map(this.mapContact);
          if (section === "companies") this.datasets.companies = records.map(this.mapClient);
          if (section === "tasks") this.datasets.tasks = records.map(this.mapTask);
          if (section === "touches") this.datasets.touches = records.map(this.mapTouch);
        },
        async loadAllSections() {
          this.isLoading = true;
          this.errorMessage = "";
          try {
            await Promise.all(
              Object.keys(SECTION_ENDPOINTS).map((section) => this.loadSection(section))
            );
          } catch (error) {
            this.errorMessage = `Ошибка загрузки данных: ${error.message}`;
          } finally {
            this.isLoading = false;
          }
        },
        async reloadActiveSection() {
          this.isLoading = true;
          this.errorMessage = "";
          try {
            await this.loadSection(this.activeSection);
          } catch (error) {
            this.errorMessage = `Ошибка обновления: ${error.message}`;
          } finally {
            this.isLoading = false;
          }
        },
        handleSourceSelectChange(section) {
          const field = section === "deals" ? this.forms.deals : this.forms.leads;
          if (!field) return;
          if (field.sourceId === "__create__") {
            field.sourceId = "";
            this.sourceCreateTargetSection = section;
            this.showSourceCreateForm = true;
            this.sourceCreateForm.name = "";
            return;
          }
          if (this.sourceCreateTargetSection === section) {
            this.cancelSourceCreate();
          }
        },
        cancelSourceCreate() {
          this.showSourceCreateForm = false;
          this.sourceCreateTargetSection = "";
          this.sourceCreateForm = { name: "" };
        },
        async createSourceFromInline(section) {
          const name = String(this.sourceCreateForm.name || "").trim();
          if (!name) {
            throw new Error("Укажите название источника");
          }
          this.isSourceSaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            const createdSource = await this.apiRequest("/api/v1/meta/lead-sources/", {
              method: "POST",
              body: {
                name,
                is_active: true
              }
            });
            await this.loadMetaOptions();
            const targetForm = section === "deals" ? this.forms.deals : this.forms.leads;
            targetForm.sourceId = createdSource.id;
            this.cancelSourceCreate();
          } catch (error) {
            this.setUiError(`Ошибка создания источника: ${error.message}`, { modal: true });
          } finally {
            this.isSourceSaving = false;
          }
        },
        setSection(section) {
          this.activeSection = section;
          window.localStorage.setItem("crm_active_section", section);
          this.search = "";
          this.showStatusFilter = false;
          this.selectedStatusFilters = [];
          this.clearTaskDealFilter();
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.showAllLeadFields = false;
          this.showAllDealFields = false;
          this.showAllCompanyFields = false;
          this.showAllTaskFields = false;
          this.showDealTaskForm = false;
          this.resetDealTaskForm();
          this.resetTaskFollowUpForm();
          this.taskTouchOptions = [];
          this.cancelSourceCreate();
          this.showDealCompanyForm = false;
          this.showDealContactsPanel = false;
          this.showDealContactForm = false;
          this.resetDealCompanyForm();
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          this.showCompanyContactForm = false;
          this.showCompanyOkvedDetails = false;
          this.resetCompanyContactForm();
          this.companyContactsForActiveCompany = [];
          if (!this.datasets[section].length) {
            this.reloadActiveSection();
          }
        },
        resetSearch() {
          this.search = "";
        },
        closeModal() {
          this.showModal = false;
          this.cancelSourceCreate();
          this.clearUiErrors({ globalOnly: true });
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.showAllLeadFields = false;
          this.showAllDealFields = false;
          this.showAllCompanyFields = false;
          this.showAllTaskFields = false;
          this.showDealTaskForm = false;
          this.resetDealTaskForm();
          this.resetTaskFollowUpForm();
          this.taskTouchOptions = [];
          this.cancelSourceCreate();
          this.showDealCompanyForm = false;
          this.showDealContactsPanel = false;
          this.showDealContactForm = false;
          this.resetDealCompanyForm();
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          this.showCompanyContactForm = false;
          this.showCompanyNoteDraft = false;
          this.showCompanyOkvedDetails = false;
          this.resetCompanyContactForm();
          this.companyContactsForActiveCompany = [];
        },
        openCreateModal() {
          this.clearUiErrors({ modalOnly: true });
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.showAllLeadFields = false;
          this.showAllDealFields = false;
          this.showAllCompanyFields = false;
          this.showCompanyNoteDraft = false;
          this.showAllTaskFields = false;
          this.showDealTaskForm = false;
          this.forms[this.activeSection] = this.getDefaultForm(this.activeSection);
          this.resetDealTaskForm();
          this.resetTaskFollowUpForm();
          this.cancelSourceCreate();
          this.showDealCompanyForm = false;
          this.showDealContactsPanel = false;
          this.showDealContactForm = false;
          this.resetDealCompanyForm();
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          this.showCompanyContactForm = false;
          this.showCompanyOkvedDetails = false;
          this.resetCompanyContactForm();
          this.companyContactsForActiveCompany = [];
          this.showModal = true;
        },
        getDefaultForm(section) {
          if (section === "leads") {
            return {
              title: "",
              description: "",
              name: "",
              company: "",
              phone: "",
              email: "",
              assignedToId: null,
              priority: "medium",
              expectedValue: "",
              statusId: this.resolveDefaultLeadStatusId(),
              sourceId: this.metaOptions.leadSources.length ? this.metaOptions.leadSources[0].id : "",
              sourceName: "",
              sourceCode: "",
              sourceNames: [],
              history: [],
              websiteSessionId: ""
            };
          }
          if (section === "deals") {
            return {
              title: "",
              description: "",
              sourceId: this.metaOptions.leadSources.length ? this.metaOptions.leadSources[0].id : "",
              companyId: null,
              ownerId: null,
              amount: "0",
              closeDate: "",
              stageId: this.metaOptions.dealStages.length ? this.metaOptions.dealStages[0].id : "",
              failureReason: "",
              events: ""
            };
          }
          if (section === "contacts") {
            return {
              fullName: "",
              companyId: null,
              position: "",
              phone: "",
              email: "",
              isPrimary: false
            };
          }
          if (section === "companies") {
            return {
              name: "",
              legalName: "",
              inn: "",
              address: "",
              industry: "",
              okved: "",
              okveds: [],
              phone: "",
              email: "",
              currency: "RUB",
              website: "",
              workRules: this.normalizeCompanyWorkRules(),
              notes: "",
              noteDraft: "",
              events: "",
              isActive: true
            };
          }
          if (section === "tasks") {
            return {
              subject: "",
              taskTypeId: null,
              priority: "medium",
              companyId: null,
              dealId: null,
              relatedTouchId: null,
              dueAt: "",
              reminderOffsetMinutes: 30,
              description: "",
              result: "",
              saveCompanyNote: false,
              companyNote: "",
              status: "todo"
            };
          }
          if (section === "touches") {
            return {
              happenedAt: "",
              channelId: null,
              direction: "outgoing",
              result: "",
              summary: "",
              nextStep: "",
              nextStepAt: "",
              ownerId: null,
              companyId: null,
              contactId: null,
              taskId: null,
              leadId: null,
              dealId: null,
            };
          }
          return {};
        },
        toIntOrNull(value) {
          if (value === null || value === undefined || value === "") {
            return null;
          }
          const parsed = Number.parseInt(value, 10);
          if (Number.isNaN(parsed)) {
            return null;
          }
          return parsed;
        },
        toIsoDateTime(value) {
          if (!value) return null;
          const parsed = new Date(value);
          if (Number.isNaN(parsed.getTime())) return null;
          return parsed.toISOString();
        },
        toDateTimeLocal(value) {
          if (!value) return "";
          const parsed = new Date(value);
          if (Number.isNaN(parsed.getTime())) return "";
          const year = parsed.getFullYear();
          const month = String(parsed.getMonth() + 1).padStart(2, "0");
          const day = String(parsed.getDate()).padStart(2, "0");
          const hours = String(parsed.getHours()).padStart(2, "0");
          const minutes = String(parsed.getMinutes()).padStart(2, "0");
          return `${year}-${month}-${day}T${hours}:${minutes}`;
        },
        async loadMetaOptions() {
          const [leadStatuses, dealStages, leadSources, users, taskTypes, communicationChannels] = await Promise.all([
            this.apiRequest("/api/v1/meta/lead-statuses/"),
            this.apiRequest("/api/v1/meta/deal-stages/"),
            this.apiRequest("/api/v1/meta/lead-sources/"),
            this.apiRequest("/api/v1/meta/users/"),
            this.apiRequest("/api/v1/meta/task-types/"),
            this.apiRequest("/api/v1/meta/communication-channels/")
          ]);
          this.metaOptions.leadStatuses = this.normalizePaginatedResponse(leadStatuses);
          this.metaOptions.dealStages = this.sortDealStages(this.normalizePaginatedResponse(dealStages));
          this.metaOptions.leadSources = this.normalizePaginatedResponse(leadSources);
          this.metaOptions.users = this.normalizePaginatedResponse(users);
          this.metaOptions.taskTypes = this.normalizePaginatedResponse(taskTypes);
          this.metaOptions.communicationChannels = this.normalizePaginatedResponse(communicationChannels);
          this.loadCurrencyRates();
        },
        async loadCurrencyRates() {
          try {
            const currencyRates = await this.apiRequest("/api/v1/meta/currency-rates/");
            this.metaOptions.currencyRates = {
              RUB: 1,
              ...((currencyRates && currencyRates.rates) || {})
            };
          } catch (error) {
            this.metaOptions.currencyRates = { RUB: 1 };
          }
        },
        async ensureClient(companyName) {
          const name = (companyName || "").trim();
          if (!name) return null;
          const clientsPayload = await this.apiRequest(`/api/v1/clients/?q=${encodeURIComponent(name)}&page_size=50`);
          const clients = this.normalizePaginatedResponse(clientsPayload);
          const exact = clients.find((client) => String(client.name || "").toLowerCase() === name.toLowerCase());
          if (exact) return exact;
          if (clients.length) return clients[0];
          return this.apiRequest("/api/v1/clients/", {
            method: "POST",
            body: { name }
          });
        },
        async createLead() {
          const form = this.forms.leads;
          if (!form.title.trim() && !form.name.trim()) {
            throw new Error("Заполните название или имя лида");
          }
          await this.apiRequest("/api/v1/leads/", {
            method: "POST",
            body: {
              title: form.title.trim() || form.name.trim(),
              description: form.description.trim(),
              name: form.name.trim(),
              company: form.company.trim(),
              phone: form.phone.trim(),
              email: form.email.trim(),
              assigned_to: this.toIntOrNull(form.assignedToId),
              priority: form.priority,
              expected_value: form.expectedValue ? Number(form.expectedValue) : null,
              status: this.toIntOrNull(form.statusId),
              source: this.toIntOrNull(form.sourceId)
            }
          });
        },
        async updateLead() {
          const form = this.forms.leads;
          if (!this.editingLeadId) {
            throw new Error("Лид для редактирования не выбран");
          }
          if (!form.title.trim() && !form.name.trim()) {
            throw new Error("Заполните название или имя лида");
          }
          await this.apiRequest(`/api/v1/leads/${this.editingLeadId}/`, {
            method: "PATCH",
            body: {
              title: form.title.trim() || form.name.trim(),
              description: form.description.trim(),
              name: form.name.trim(),
              company: form.company.trim(),
              phone: form.phone.trim(),
              email: form.email.trim(),
              assigned_to: this.toIntOrNull(form.assignedToId),
              priority: form.priority,
              expected_value: form.expectedValue ? Number(form.expectedValue) : null,
              status: this.toIntOrNull(form.statusId),
              source: this.toIntOrNull(form.sourceId)
            }
          });
        },
        async updateDeal() {
          const form = this.forms.deals;
          if (!this.editingDealId) {
            throw new Error("Сделка для редактирования не выбрана");
          }
          if (!form.title.trim()) {
            throw new Error("Укажите название сделки");
          }
          if (!this.toIntOrNull(form.sourceId)) {
            throw new Error("Выберите источник сделки");
          }
          const clientId = this.toIntOrNull(form.companyId);
          const ownerId = this.toIntOrNull(form.ownerId);
          return this.apiRequest(`/api/v1/deals/${this.editingDealId}/`, {
            method: "PATCH",
            body: {
              title: form.title.trim(),
              description: form.description.trim(),
              source: this.toIntOrNull(form.sourceId),
              client: clientId,
              owner: ownerId,
              amount: Number(form.amount || 0),
              close_date: form.closeDate || null,
              stage: this.toIntOrNull(form.stageId),
              is_won: this.resolveDealWonFlag(form.stageId),
              has_pending_task: this.hasPendingDealTaskDraft(),
              failure_reason: form.failureReason.trim()
            }
          });
        },
        async createDeal() {
          const form = this.forms.deals;
          if (!form.title.trim()) {
            throw new Error("Укажите название сделки");
          }
          if (!this.toIntOrNull(form.sourceId)) {
            throw new Error("Выберите источник сделки");
          }
          const clientId = this.toIntOrNull(form.companyId);
          const ownerId = this.toIntOrNull(form.ownerId);
          return this.apiRequest("/api/v1/deals/", {
            method: "POST",
            body: {
              title: form.title.trim(),
              description: form.description.trim(),
              source: this.toIntOrNull(form.sourceId),
              client: clientId,
              owner: ownerId,
              amount: Number(form.amount || 0),
              close_date: form.closeDate || null,
              stage: this.toIntOrNull(form.stageId),
              is_won: this.resolveDealWonFlag(form.stageId),
              has_pending_task: this.hasPendingDealTaskDraft(),
              failure_reason: form.failureReason.trim()
            }
          });
        },
        async createTaskFromDeal(dealId = null) {
          const targetDealId = this.toIntOrNull(dealId) || this.editingDealId;
          if (!targetDealId) {
            throw new Error("Сначала откройте сделку");
          }
          const subject = this.dealTaskForm.subject.trim();
          if (!subject) {
            throw new Error("Укажите название задачи");
          }
          if (!this.dealTaskForm.dueAt) {
            throw new Error("Укажите срок задачи");
          }
          this.isDealTaskSaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.apiRequest("/api/v1/activities/", {
              method: "POST",
              body: {
                type: "task",
                subject,
                description: this.dealTaskForm.description.trim(),
                due_at: this.toIsoDateTime(this.dealTaskForm.dueAt),
                deadline_reminder_offset_minutes: Number(this.dealTaskForm.reminderOffsetMinutes || 30),
                deal: targetDealId,
                client: this.toIntOrNull(this.forms.deals.companyId)
              }
            });
            this.resetDealTaskForm();
            this.showDealTaskForm = false;
            await this.loadTasksForDeal();
            await this.loadSection("tasks");
          } catch (error) {
            this.setUiError(`Ошибка создания задачи: ${error.message}`, { modal: true });
          } finally {
            this.isDealTaskSaving = false;
          }
        },
        async createCompanyFromDeal() {
          const companyName = this.dealCompanyForm.name.trim();
          if (!companyName) {
            throw new Error("Укажите название компании");
          }

          this.isDealCompanySaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            const createdCompany = await this.apiRequest("/api/v1/clients/", {
              method: "POST",
              body: {
                name: companyName,
                inn: this.dealCompanyForm.inn.trim() || null,
                address: this.dealCompanyForm.address.trim(),
                industry: this.dealCompanyForm.industry.trim(),
                okved: this.dealCompanyForm.okved.trim(),
                phone: this.dealCompanyForm.phone.trim(),
                email: this.dealCompanyForm.email.trim(),
                currency: this.dealCompanyForm.currency || "RUB",
                website: this.dealCompanyForm.website.trim(),
                is_active: true
              }
            });
            this.forms.deals.companyId = createdCompany.id;
            this.resetDealCompanyForm();
            this.showDealCompanyForm = false;
            this.showDealContactsPanel = true;
            this.showDealContactForm = true;
            await this.loadSection("companies");
            await this.loadContactsForSelectedDealCompany();
          } catch (error) {
            this.setUiError(`Ошибка создания компании: ${error.message}`, { modal: true });
          } finally {
            this.isDealCompanySaving = false;
          }
        },
        async createContactFromDealSelectedCompany() {
          const clientId = this.toIntOrNull(this.forms.deals.companyId);
          if (!clientId) {
            throw new Error("Сначала выберите компанию");
          }
          const fullName = this.dealCompanyContactForm.fullName.trim();
          if (!fullName) {
            throw new Error("Укажите ФИО контакта");
          }
          this.isDealCompanySaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            const parts = fullName.split(/\s+/).filter(Boolean);
            const firstName = parts[0] || fullName;
            const lastName = parts.slice(1).join(" ");
            await this.apiRequest("/api/v1/contacts/", {
              method: "POST",
              body: {
                client: clientId,
                first_name: firstName,
                last_name: lastName,
                position: this.dealCompanyContactForm.position.trim(),
                phone: this.dealCompanyContactForm.phone.trim(),
                email: this.dealCompanyContactForm.email.trim(),
                is_primary: !!this.dealCompanyContactForm.isPrimary
              }
            });
            this.resetDealCompanyContactForm();
            this.showDealContactForm = false;
            await this.loadContactsForSelectedDealCompany();
            await this.loadSection("contacts");
          } catch (error) {
            this.setUiError(`Ошибка создания контакта: ${error.message}`, { modal: true });
          } finally {
            this.isDealCompanySaving = false;
          }
        },
        async createContact() {
          const form = this.forms.contacts;
          if (!form.fullName.trim()) {
            throw new Error("Укажите имя контакта");
          }
          const clientId = this.toIntOrNull(form.companyId);
          if (!clientId) {
            throw new Error("Для контакта требуется компания");
          }
          const parts = form.fullName.trim().split(/\s+/).filter(Boolean);
          const firstName = parts[0] || form.fullName;
          const lastName = parts.slice(1).join(" ");
          await this.apiRequest("/api/v1/contacts/", {
            method: "POST",
            body: {
              client: clientId,
              first_name: firstName,
              last_name: lastName,
              position: form.position.trim(),
              phone: form.phone.trim(),
              email: form.email.trim(),
              is_primary: !!form.isPrimary
            }
          });
        },
        async updateContact() {
          const form = this.forms.contacts;
          if (!this.editingContactId) {
            throw new Error("Контакт для редактирования не выбран");
          }
          if (!form.fullName.trim()) {
            throw new Error("Укажите имя контакта");
          }
          const clientId = this.toIntOrNull(form.companyId);
          if (!clientId) {
            throw new Error("Для контакта требуется компания");
          }
          const parts = form.fullName.trim().split(/\s+/).filter(Boolean);
          const firstName = parts[0] || form.fullName;
          const lastName = parts.slice(1).join(" ");
          await this.apiRequest(`/api/v1/contacts/${this.editingContactId}/`, {
            method: "PATCH",
            body: {
              client: clientId,
              first_name: firstName,
              last_name: lastName,
              position: form.position.trim(),
              phone: form.phone.trim(),
              email: form.email.trim(),
              is_primary: !!form.isPrimary
            }
          });
        },
        async createCompany() {
          const form = this.forms.companies;
          if (!form.name.trim()) {
            throw new Error("Укажите название компании");
          }
          await this.apiRequest("/api/v1/clients/", {
            method: "POST",
            body: {
              name: form.name.trim(),
              legal_name: form.legalName.trim(),
              inn: form.inn.trim() || null,
              address: form.address.trim(),
              industry: form.industry.trim(),
              okved: form.okved.trim(),
              okveds: this.normalizeCompanyOkveds(form.okveds, form.okved, form.industry),
              phone: form.phone.trim(),
              email: form.email.trim(),
              currency: form.currency || "RUB",
              website: form.website.trim(),
              work_rules: this.serializeCompanyWorkRules(form.workRules),
              note_draft: form.noteDraft.trim(),
              is_active: !!form.isActive
            }
          });
        },
        async updateCompany() {
          const form = this.forms.companies;
          if (!this.editingCompanyId) {
            throw new Error("Компания для редактирования не выбрана");
          }
          if (!form.name.trim()) {
            throw new Error("Укажите название компании");
          }
          await this.apiRequest(`/api/v1/clients/${this.editingCompanyId}/`, {
            method: "PATCH",
            body: {
              name: form.name.trim(),
              legal_name: form.legalName.trim(),
              inn: form.inn.trim() || null,
              address: form.address.trim(),
              industry: form.industry.trim(),
              okved: form.okved.trim(),
              okveds: this.normalizeCompanyOkveds(form.okveds, form.okved, form.industry),
              phone: form.phone.trim(),
              email: form.email.trim(),
              currency: form.currency || "RUB",
              website: form.website.trim(),
              work_rules: this.serializeCompanyWorkRules(form.workRules),
              note_draft: form.noteDraft.trim(),
              is_active: !!form.isActive
            }
          });
        },
        async createContactFromCompany() {
          if (!this.editingCompanyId) {
            throw new Error("Сначала откройте компанию");
          }
          const fullName = this.companyContactForm.fullName.trim();
          if (!fullName) {
            throw new Error("Укажите ФИО контакта");
          }
          const parts = fullName.split(/\s+/).filter(Boolean);
          const firstName = parts[0] || fullName;
          const lastName = parts.slice(1).join(" ");
          this.isCompanyContactSaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.apiRequest("/api/v1/contacts/", {
              method: "POST",
              body: {
                client: this.editingCompanyId,
                first_name: firstName,
                last_name: lastName,
                position: this.companyContactForm.position.trim(),
                phone: this.companyContactForm.phone.trim(),
                email: this.companyContactForm.email.trim(),
                is_primary: !!this.companyContactForm.isPrimary
              }
            });
            this.resetCompanyContactForm();
            this.showCompanyContactForm = false;
            await this.loadContactsForCompany();
            await this.loadSection("contacts");
          } catch (error) {
            this.setUiError(`Ошибка создания контакта: ${error.message}`, { modal: true });
          } finally {
            this.isCompanyContactSaving = false;
          }
        },
        async createTask() {
          const form = this.forms.tasks;
          if (!form.subject.trim()) {
            throw new Error("Укажите название задачи");
          }
          if (!form.dueAt) {
            throw new Error("Укажите срок задачи");
          }
          if (form.saveCompanyNote && !form.companyNote.trim()) {
            throw new Error("Укажите важные факты о компании");
          }
          if (this.isTaskDoneStatus(form.status) && !form.result.trim()) {
            throw new Error("Укажите результат выполнения задачи");
          }
          this.validateTaskFollowUpRequirement();
          const clientId = this.toIntOrNull(form.companyId);
          await this.apiRequest("/api/v1/activities/", {
            method: "POST",
            body: {
              type: "task",
              subject: form.subject.trim(),
              task_type: this.toIntOrNull(form.taskTypeId),
              priority: form.priority || "medium",
              description: form.description.trim(),
              result: form.result.trim(),
              due_at: this.toIsoDateTime(form.dueAt),
              deadline_reminder_offset_minutes: Number(form.reminderOffsetMinutes || 30),
              client: clientId,
              deal: this.toIntOrNull(form.dealId),
              related_touch: this.toIntOrNull(form.relatedTouchId),
              has_follow_up_task: this.hasPreparedTaskFollowUp(),
              save_company_note: !!form.saveCompanyNote,
              company_note: form.companyNote.trim(),
              status: form.status || "todo"
            }
          });
        },
        async updateTask() {
          const form = this.forms.tasks;
          if (!this.editingTaskId) {
            throw new Error("Задача для редактирования не выбрана");
          }
          if (!form.subject.trim()) {
            throw new Error("Укажите название задачи");
          }
          if (!form.dueAt) {
            throw new Error("Укажите срок задачи");
          }
          if (form.saveCompanyNote && !form.companyNote.trim()) {
            throw new Error("Укажите важные факты о компании");
          }
          if (this.isTaskDoneStatus(form.status) && !form.result.trim()) {
            throw new Error("Укажите результат выполнения задачи");
          }
          this.validateTaskFollowUpRequirement();
          const clientId = this.toIntOrNull(form.companyId);
          await this.apiRequest(`/api/v1/activities/${this.editingTaskId}/`, {
            method: "PATCH",
            body: {
              type: "task",
              subject: form.subject.trim(),
              task_type: this.toIntOrNull(form.taskTypeId),
              priority: form.priority || "medium",
              description: form.description.trim(),
              result: form.result.trim(),
              due_at: this.toIsoDateTime(form.dueAt),
              deadline_reminder_offset_minutes: Number(form.reminderOffsetMinutes || 30),
              client: clientId,
              deal: this.toIntOrNull(form.dealId),
              related_touch: this.toIntOrNull(form.relatedTouchId),
              has_follow_up_task: this.hasPreparedTaskFollowUp(),
              save_company_note: !!form.saveCompanyNote,
              company_note: form.companyNote.trim(),
              status: form.status || "todo"
            }
          });
        },
        validateTouchForm(form) {
          if (!form.happenedAt) {
            throw new Error("Укажите дату и время касания");
          }
          if (
            !this.toIntOrNull(form.leadId)
            && !this.toIntOrNull(form.dealId)
            && !this.toIntOrNull(form.companyId)
            && !this.toIntOrNull(form.contactId)
            && !this.toIntOrNull(form.taskId)
          ) {
            throw new Error("Привяжите касание хотя бы к одному объекту CRM");
          }
        },
        async createTouch() {
          const form = this.forms.touches;
          this.validateTouchForm(form);
          await this.apiRequest("/api/v1/touches/", {
            method: "POST",
            body: {
              happened_at: this.toIsoDateTime(form.happenedAt),
              channel: this.toIntOrNull(form.channelId),
              direction: form.direction || "outgoing",
              result: form.result.trim(),
              summary: form.summary.trim(),
              next_step: form.nextStep.trim(),
              next_step_at: this.toIsoDateTime(form.nextStepAt),
              owner: this.toIntOrNull(form.ownerId),
              client: this.toIntOrNull(form.companyId),
              contact: this.toIntOrNull(form.contactId),
              task: this.toIntOrNull(form.taskId),
              lead: this.toIntOrNull(form.leadId),
              deal: this.toIntOrNull(form.dealId),
            }
          });
        },
        async updateTouch() {
          const form = this.forms.touches;
          if (!this.editingTouchId) {
            throw new Error("Касание для редактирования не выбрано");
          }
          this.validateTouchForm(form);
          await this.apiRequest(`/api/v1/touches/${this.editingTouchId}/`, {
            method: "PATCH",
            body: {
              happened_at: this.toIsoDateTime(form.happenedAt),
              channel: this.toIntOrNull(form.channelId),
              direction: form.direction || "outgoing",
              result: form.result.trim(),
              summary: form.summary.trim(),
              next_step: form.nextStep.trim(),
              next_step_at: this.toIsoDateTime(form.nextStepAt),
              owner: this.toIntOrNull(form.ownerId),
              client: this.toIntOrNull(form.companyId),
              contact: this.toIntOrNull(form.contactId),
              task: this.toIntOrNull(form.taskId),
              lead: this.toIntOrNull(form.leadId),
              deal: this.toIntOrNull(form.dealId),
            }
          });
        },
        async createFollowUpTaskFromCurrentDeal() {
          const followUp = this.taskFollowUpForm;
          const subject = followUp.subject.trim();
          const dealId = this.toIntOrNull(this.forms.tasks.dealId);
          if (!subject || !dealId || !followUp.dueAt) {
            return;
          }
          await this.apiRequest("/api/v1/activities/", {
            method: "POST",
            body: {
              type: "task",
              subject,
              description: followUp.description.trim(),
              due_at: this.toIsoDateTime(followUp.dueAt),
              deadline_reminder_offset_minutes: Number(followUp.reminderOffsetMinutes || 30),
              client: this.toIntOrNull(this.forms.tasks.companyId),
              deal: dealId,
              status: "todo"
            }
          });
        },
        async createItem() {
          this.isSaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            let savedDeal = null;
            if (this.activeSection === "leads" && this.editingLeadId) await this.updateLead();
            if (this.activeSection === "leads" && !this.editingLeadId) await this.createLead();
            if (this.activeSection === "deals") {
              this.validateDealCompanyRequirement();
              this.validateDealFailureReason();
              this.validateDealTaskRequirement();
              this.validatePendingDealTaskDraft();
            }
            if (this.activeSection === "deals" && this.editingDealId) savedDeal = await this.updateDeal();
            if (this.activeSection === "deals" && !this.editingDealId) savedDeal = await this.createDeal();
            if (this.activeSection === "deals" && this.hasPendingDealTaskDraft()) {
              await this.createTaskFromDeal(savedDeal && savedDeal.id ? savedDeal.id : this.editingDealId);
            }
            if (this.activeSection === "contacts" && this.editingContactId) await this.updateContact();
            if (this.activeSection === "contacts" && !this.editingContactId) await this.createContact();
            if (this.activeSection === "companies" && this.editingCompanyId) await this.updateCompany();
            if (this.activeSection === "companies" && !this.editingCompanyId) await this.createCompany();
            if (this.activeSection === "tasks" && this.editingTaskId) await this.updateTask();
            if (this.activeSection === "tasks" && this.editingTaskId && this.showTaskFollowUpSuggestion && this.taskFollowUpForm.subject.trim()) {
              await this.createFollowUpTaskFromCurrentDeal();
            }
            if (this.activeSection === "tasks" && !this.editingTaskId) await this.createTask();
            if (this.activeSection === "touches" && this.editingTouchId) await this.updateTouch();
            if (this.activeSection === "touches" && !this.editingTouchId) await this.createTouch();
            this.showModal = false;
            this.cancelSourceCreate();
            this.editingLeadId = null;
            this.editingDealId = null;
            this.editingContactId = null;
            this.editingCompanyId = null;
            this.editingTaskId = null;
            this.editingTouchId = null;
            this.showDealTaskForm = false;
            this.resetDealTaskForm();
            this.resetTaskFollowUpForm();
            this.showDealCompanyForm = false;
            this.resetDealCompanyForm();
            this.dealTasksForActiveDeal = [];
            this.showCompanyContactForm = false;
            this.resetCompanyContactForm();
            this.companyContactsForActiveCompany = [];
            if (this.activeSection === "leads") {
              await Promise.all([this.loadSection("leads"), this.loadSection("deals")]);
            } else if (this.activeSection === "deals") {
              await Promise.all([this.loadSection("deals"), this.loadSection("companies")]);
            } else if (this.activeSection === "tasks") {
              await Promise.all([this.loadSection("tasks"), this.loadSection("deals"), this.loadSection("companies")]);
            } else if (this.activeSection === "touches") {
              await Promise.all([this.loadSection("touches"), this.loadSection("leads"), this.loadSection("deals")]);
            } else {
              await this.reloadActiveSection();
            }
          } catch (error) {
            this.setUiError(`Ошибка сохранения: ${error.message}`, { modal: true });
          } finally {
            this.isSaving = false;
          }
        },
        statusClass(status) {
          if (["lost", "unqualified", "spam"].includes(status)) {
            return "border-red-400/30 bg-red-400/10 text-red-300";
          }
          if (["converted", "archived", "done"].includes(status)) {
            return "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";
          }
          if (["in_progress", "qualified", "attempting_contact", "progress"].includes(status)) {
            return "border-sky-400/30 bg-sky-400/10 text-sky-300";
          }
          return "border-amber-400/30 bg-amber-400/10 text-amber-300";
        },
        hideStartupScreen() {
          const overlay = document.getElementById("crm-startup-screen");
          if (!overlay) return;
          overlay.classList.add("is-hidden");
          window.setTimeout(() => {
            overlay.remove();
            document.body.classList.remove("crm-startup-screen-active");
          }, 240);
        }
      },
      async mounted() {
        document.addEventListener("click", this.handleDocumentClick);
        document.addEventListener("keydown", this.handleGlobalKeydown);
        const savedSection = window.localStorage.getItem("crm_active_section");
        if (savedSection && Object.prototype.hasOwnProperty.call(SECTION_ENDPOINTS, savedSection)) {
          this.activeSection = savedSection;
        }
        try {
          await this.loadMetaOptions();
        } catch (error) {
          this.errorMessage = `Ошибка загрузки справочников: ${error.message}`;
        }
        await this.loadAllSections();
        window.setTimeout(() => this.hideStartupScreen(), 500);
      },
      beforeUnmount() {
        document.removeEventListener("click", this.handleDocumentClick);
        document.removeEventListener("keydown", this.handleGlobalKeydown);
      }
    }).mount("#app");
