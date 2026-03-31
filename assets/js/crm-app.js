    const { createApp } = Vue;
    const appRootElement = document.getElementById("app");
    const appRootTemplate = appRootElement ? String(appRootElement.innerHTML || "") : "";
    const currentUserId = appRootElement
      ? (Number.parseInt(appRootElement.dataset.currentUserId || "", 10) || null)
      : null;
    const currentUserCanViewAllCommunications = appRootElement
      ? String(appRootElement.dataset.currentUserCanViewAllCommunications || "").trim().toLowerCase() === "true"
      : false;

    const SECTION_ENDPOINTS = {
      leads: "/api/v1/leads/?page_size=100",
      deals: "/api/v1/deals/?page_size=100",
      contacts: "/api/v1/contacts/?page_size=100",
      companies: "/api/v1/clients/?page_size=100",
      tasks: "/api/v1/activities/?type=task&page_size=100",
      touches: "/api/v1/touches/?page_size=100"
    };
    const FILTERS_STORAGE_KEY = "crm_section_filters";
    const TIMELINE_FILTER_OPTIONS = [
      { value: "messages", label: "Сообщения" },
      { value: "email", label: "Email" },
      { value: "touches", label: "Касания" },
      { value: "tasks", label: "Задачи" }
    ];

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
      { value: "todo", label: "Новая" },
      { value: "in_progress", label: "В работе" },
      { value: "done", label: "Выполнено" },
      { value: "canceled", label: "Отменено" }
    ];

    const TASK_PRIORITY_OPTIONS = [
      { value: "low", label: "Низкий" },
      { value: "medium", label: "Средний" },
      { value: "high", label: "Высокий" }
    ];

    const SETTLEMENT_DOCUMENT_TYPE_OPTIONS = [
      { value: "invoice", label: "Счет" },
      { value: "realization", label: "Акт / накладная" },
      { value: "supplier_receipt", label: "Поступление от поставщика" },
      { value: "incoming_payment", label: "Оплата входящая" },
      { value: "outgoing_payment", label: "Оплата исходящая" },
      { value: "debt_adjustment", label: "Корректировка долга" },
      { value: "refund", label: "Возврат" },
    ];

    const SETTLEMENT_DIRECTION_OPTIONS = [
      { value: "incoming", label: "Входящий" },
      { value: "outgoing", label: "Исходящий" },
    ];

    const SETTLEMENT_REALIZATION_STATUS_OPTIONS = [
      { value: "created", label: "Создан" },
      { value: "sent_to_client", label: "Отправлен клиенту" },
      { value: "signed", label: "Подписан" },
    ];
    const COMPANY_TYPE_OPTIONS = [
      { value: "own", label: "Собственные организации" },
      { value: "client", label: "Клиент" },
      { value: "supplier", label: "Поставщик" },
    ];

    const SETTLEMENT_DIRECTION_REQUIRED_TYPES = ["debt_adjustment", "refund"];

    const app = createApp({
      compilerOptions: {
        delimiters: ["[[", "]]"]
      },
      ...(appRootTemplate ? { template: appRootTemplate } : {}),
      data() {
        return {
          activeSection: "leads",
          search: "",
          showModal: false,
          currentUserId,
          currentUserCanViewAllCommunications,
          modalParentContext: null,
          isSectionLazyLoadingReady: false,
          isLoading: false,
          isSaving: false,
          showStatusFilter: false,
          showDealCompanyFilter: false,
          showTaskCompanyFilter: false,
          showTaskCategoryFilter: false,
          showTaskDealFilter: false,
          showTouchCompanyFilter: false,
          showTouchDealFilter: false,
          showManagerNotifications: false,
          showManagerNotificationSidebar: false,
          activeManagerNotificationId: "",
          managerNotificationSidebarMode: "overview",
          managerNotificationDraftPreviewId: "",
          managerNotificationReplyDraftId: "",
          managerNotificationReplyStates: {},
          isManagerNotificationReplySending: false,
          managerNotificationReplyComposer: {
            subject: "",
            bodyText: "",
            recipient: "",
          },
          isUnboundCommunicationsLoading: false,
          isUnboundConversationMessagesLoading: false,
          isUnboundConversationBinding: false,
          isUnboundCommunicationSending: false,
          communicationsCompanies: [],
          communicationsDeals: [],
          communicationsContacts: [],
          communicationsConversations: [],
          communicationsMessages: [],
          communicationsCalls: [],
          communicationsTimelineFilter: "all",
          communicationsSelectedCompanyId: null,
          communicationsSelectedTimelineItemKey: "",
          communicationsComposerMode: "",
          communicationsComposer: {
            contactId: null,
            recipient: "",
            subject: "",
            bodyText: "",
          },
          communicationsPendingDealDocument: null,
          communicationsContextDealId: null,
          isCommunicationsCompaniesLoading: false,
          isCommunicationsContactsLoading: false,
          isCommunicationsTimelineLoading: false,
          isCommunicationsSending: false,
          selectedStatusFilters: [],
          statusFiltersBySection: {
            leads: [],
            deals: [],
            contacts: [],
            companies: [],
            tasks: [],
            touches: [],
          },
          statsQuickFilterBySection: {
            leads: "",
            deals: "",
            companies: "",
            tasks: "",
          },
          selectedTaskCompanyFilters: [],
          selectedTaskCategoryFilters: [],
          selectedTouchCompanyFilters: [],
          editingLeadId: null,
          editingDealId: null,
          editingContactId: null,
          editingCompanyId: null,
          editingTaskId: null,
          editingTouchId: null,
          isDealTaskSaving: false,
          isDealTasksLoading: false,
          showDealTaskForm: false,
          isDealCompanySaving: false,
          isSourceSaving: false,
          showDealCompanyForm: false,
          showDealContactsPanel: false,
          showDealDocumentsPanel: false,
          showLeadDocumentsPanel: false,
          showDealCommunicationsPanel: false,
          showDealDocumentSendSidebar: false,
          showDealContactForm: false,
          isDealContactsLoading: false,
          isDealDocumentsLoading: false,
          isDealCommunicationsLoading: false,
          isDealDocumentSendSidebarPreparing: false,
          isDealDocumentSendLoading: false,
          isDealDocumentDeliveryHistoryLoading: false,
          isDealDocumentSendMessagesLoading: false,
          isDealConversationMessagesLoading: false,
          isDealCommunicationSending: false,
          isDealCommunicationStarting: false,
          isDealDocumentSendSending: false,
          isDealDocumentSendStarting: false,
          isDealDocumentUploading: false,
          isDealActGeneratorPreparing: false,
          isDealActGenerating: false,
          isTouchDocumentsLoading: false,
          isTouchDocumentUploading: false,
          touchResultPromptVisible: false,
          touchResultPromptText: "",
          showAllTouchResults: false,
          automationDataLoaded: false,
          automationDataLoadPromise: null,
          isCompanyContactSaving: false,
          isCompanyContactsLoading: false,
          isCompanyDocumentsLoading: false,
          isLeadDocumentsLoading: false,
          isCompanyCommunicationsLoading: false,
          isCompanyConversationMessagesLoading: false,
          isCompanyCommunicationSending: false,
          isCompanyDocumentUploading: false,
          isLeadDocumentUploading: false,
          isTaskTouchesLoading: false,
          showCompanyContactForm: false,
          showCompanyContactsPanel: false,
          showCompanyDocumentsPanel: false,
          showCompanyCommunicationsPanel: false,
          showCompanyDealsPanel: false,
          showCompanyLeadsPanel: false,
          showCompanyWorkRules: false,
          showCompanyPhoneCallHistory: false,
          showCompanyNoteDraft: false,
          showCompanyOkvedDetails: false,
          showCompanyRequisites: false,
          showCompanySettlementsPanel: false,
          showCompanySettlementContractForm: false,
          showCompanySettlementDocumentForm: false,
          showCompanySettlementAllocationForm: false,
          isCompanySettlementsLoading: false,
          isCompanySettlementSaving: false,
          leadSummaryEditingField: "",
          dealSummaryEditingField: "",
          taskSummaryEditingField: "",
          companySummaryEditingField: "",
          expandedOptionalFields: {
            leads: {},
            deals: {},
            companies: {},
            tasks: {}
          },
          expandedCompanyCards: {},
          showCompanyEvents: false,
          dealCompanyFilterId: null,
          dealCompanyFilterLabel: "",
          taskDealFilterId: null,
          taskDealFilterLabel: "",
          touchDealFilterId: null,
          touchDealFilterLabel: "",
          taskTouchOptions: [],
          showSourceCreateForm: false,
          sourceCreateTargetSection: "",
          sourceCreateForm: {
            name: ""
          },
          errorMessage: "",
          modalErrorMessage: "",
          isNovofonCallStarting: false,
          activeNovofonCallTarget: "",
          telephonyNotice: {
            type: "",
            text: "",
          },
          isTelephonySettingsLoading: false,
          isTelephonySettingsSaving: false,
          isTelephonyConnectionChecking: false,
          isTelephonyEmployeesSyncing: false,
          isTelephonyCallsImporting: false,
          isTelephonyHealthLoading: false,
          telephonyHealth: {
            counts: {
              queued: 0,
              failed: 0,
              processing: 0,
              staleProcessing: 0,
              processed: 0,
              ignoredDuplicate: 0,
            },
            latestEventAt: "",
            oldestQueuedAt: "",
            staleProcessingAfterSeconds: 0,
            problemEvents: [],
          },
          telephonySettingsLoaded: false,
          telephonyLastImportResult: null,
          telephonyIncomingCallCursor: 0,
          telephonyIncomingCallPopups: [],
          isTelephonyIncomingCallsPolling: false,
          telephonyIncomingCallsPollTimer: null,
          telephonyImportForm: {
            days: 30,
            limit: 500,
            maxRecords: 5000,
            includeOngoingCalls: false,
          },
          telephonySettings: {
            enabled: false,
            apiBaseUrl: "",
            webhookPath: "",
            webhookUrl: "",
            defaultOwnerId: null,
            createLeadForUnknownNumber: false,
            createTaskForMissedCall: false,
            linkCallsToOpenDealOnly: true,
            allowedVirtualNumbersText: "",
            isDebugLoggingEnabled: false,
            hasApiSecret: false,
            lastConnectionCheckedAt: "",
            lastConnectionStatus: "",
            lastConnectionError: "",
            mappings: [],
            settingsJson: {},
          },
          phoneCallHistoryFilters: [
            { value: "all", label: "Все" },
            { value: "inbound", label: "Входящие" },
            { value: "outbound", label: "Исходящие" },
            { value: "missed", label: "Пропущенные" },
          ],
          timelineFilterOptions: TIMELINE_FILTER_OPTIONS.slice(),
          timelineFilters: {
            leads: TIMELINE_FILTER_OPTIONS.map((item) => item.value),
            deals: TIMELINE_FILTER_OPTIONS.map((item) => item.value),
            companies: TIMELINE_FILTER_OPTIONS.map((item) => item.value),
          },
          phoneCallHistories: {},
          showDealPhoneCallHistory: false,
          showLeadPhoneCallHistory: false,
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
              websiteSessionId: "",
              events: ""
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
              telegram: "",
              whatsapp: "",
              maxContact: "",
              roleId: null,
              role: "",
              personNote: "",
              isPrimary: false
            },
            companies: {
              name: "",
              legalName: "",
              inn: "",
              companyType: "client",
              address: "",
              actualAddress: "",
              ogrn: "",
              kpp: "",
              bankDetails: "",
              settlementAccount: "",
              correspondentAccount: "",
              iban: "",
              bik: "",
              bankName: "",
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
              taskCategoryId: null,
              taskTypeId: null,
              communicationChannelId: null,
              priority: "medium",
              ownerId: currentUserId,
              companyId: null,
              leadId: null,
              dealId: null,
              relatedTouchId: null,
              dueAt: "",
              reminderOffsetMinutes: 30,
              checklist: [],
              description: "",
              result: "",
              saveCompanyNote: false,
              companyNote: "",
              status: "todo"
            },
            touches: {
              happenedAt: "",
              channelId: null,
              resultOptionId: null,
              direction: "outgoing",
              summary: "",
              nextStep: "",
              nextStepAt: "",
              ownerId: null,
              companyId: null,
              contactId: null,
              taskId: null,
              leadId: null,
              dealId: null,
              dealDocumentIds: [],
              clientDocumentIds: [],
              documentUploadTarget: ""
            }
          },
          dealTaskForm: {
            subject: "",
            taskCategoryId: null,
            taskTypeId: null,
            communicationChannelId: null,
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          },
          touchFollowUpForm: {
            subject: "",
            taskCategoryId: null,
            taskTypeId: null,
            communicationChannelId: null,
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          },
          taskFollowUpForm: {
            subject: "",
            taskCategoryId: null,
            taskTypeId: null,
            communicationChannelId: null,
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          },
          dealCompanyForm: {
            name: "",
            inn: "",
            companyType: "client",
            address: "",
            actualAddress: "",
            bankDetails: "",
            iban: "",
            bik: "",
            bankName: "",
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
          dealDocumentsForActiveDeal: [],
          dealDocumentSendTarget: null,
          showDealActGenerator: false,
          dealDocumentGeneratorType: "",
          dealDocumentGeneratorMode: "create",
          dealDocumentGeneratorTargetDocumentId: null,
          dealDocumentGeneratorTargetName: "",
          dealActGeneratorForm: {
            executorCompanyId: null,
            contractId: null,
            items: [],
          },
          dealDocumentGeneratorContracts: [],
          leadDocumentsForActiveLead: [],
          dealCommunications: [],
          dealManualBindingConversations: [],
          dealConversationMessages: [],
          activeDealConversationId: null,
          dealDocumentSendConversations: [],
          dealDocumentDeliveryHistory: [],
          dealDocumentSendMessages: [],
          activeDealDocumentSendConversationId: null,
          showDealDocumentSendStartForm: false,
          showDealCommunicationStartForm: false,
          dealCommunicationComposer: {
            subject: "",
            bodyText: "",
            recipient: ""
          },
          dealDocumentSendComposer: {
            subject: "",
            bodyText: "",
            recipient: ""
          },
          dealCommunicationStartForm: {
            channel: "email",
            contactId: null,
            recipient: "",
            subject: "",
            bodyText: ""
          },
          dealDocumentSendStartForm: {
            channel: "email",
            contactId: null,
            recipient: "",
            subject: "",
            bodyText: ""
          },
          touchDealDocuments: [],
          touchCompanyDocuments: [],
          dealCompanyContacts: [],
          companyContactForm: {
            fullName: "",
            position: "",
            phone: "",
            email: "",
            telegram: "",
            whatsapp: "",
            maxContact: "",
            roleId: null,
            role: "",
            personNote: "",
            isPrimary: false
          },
          companyContactsForActiveCompany: [],
          companyDocumentsForActiveCompany: [],
          companyDealDocumentGroups: [],
          companySettlementContracts: [],
          companySettlementDocuments: [],
          companySettlementDocumentStatusSaving: {},
          companySettlementSummary: {
            overview: {
              expectedReceivable: 0,
              receivable: 0,
              payable: 0,
              advancesReceived: 0,
              advancesIssued: 0,
              overdue: 0,
              nearestDueDate: "",
              balance: 0,
            },
            contracts: [],
          },
          companySettlementContractForm: {
            id: null,
            title: "",
            number: "",
            currency: "RUB",
            hourlyRate: "",
            startDate: "",
            endDate: "",
            note: "",
            isActive: true,
          },
          companySettlementDocumentForm: {
            contractId: null,
            dealId: null,
            documentType: "invoice",
            flowDirection: "",
            title: "",
            number: "",
            documentDate: "",
            dueDate: "",
            amount: "",
            currency: "RUB",
            realizationStatus: "",
            note: "",
            file: null,
            fileName: "",
          },
          companySettlementAllocationForm: {
            sourceDocumentId: null,
            targetDocumentId: null,
            amount: "",
            allocatedAt: "",
            note: "",
          },
          settlementDocumentTypeOptions: SETTLEMENT_DOCUMENT_TYPE_OPTIONS.slice(),
          settlementDirectionOptions: SETTLEMENT_DIRECTION_OPTIONS.slice(),
          settlementRealizationStatusOptions: SETTLEMENT_REALIZATION_STATUS_OPTIONS.slice(),
          companyTypeOptions: COMPANY_TYPE_OPTIONS.slice(),
          companyCommunications: [],
          companyConversationMessages: [],
          activeCompanyConversationId: null,
          companyCommunicationComposer: {
            subject: "",
            bodyText: "",
            recipient: ""
          },
          activeAutomationMessageDraftPreview: null,
          unboundConversations: [],
          unboundConversationMessages: [],
          activeUnboundConversationId: null,
          unboundConversationBindForm: {
            clientId: null,
            contactId: null,
            dealId: null,
          },
          unboundCommunicationComposer: {
            subject: "",
            bodyText: "",
            recipient: "",
          },
          communicationsPollTimer: null,
          automationNotificationsPollTimer: null,
          isAutomationNotificationsPolling: false,
          metaOptions: {
            leadStatuses: [],
            dealStages: [],
            leadSources: [],
            users: [],
            taskCategories: [],
            taskTypes: [],
            touchResults: [],
            outcomes: [],
            nextStepTemplates: [],
            automationRules: [],
            communicationChannels: [],
            contactRoles: [],
            contactStatuses: [],
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
          taskChecklistHideCompleted: false,
          sidebarItems: [
            { key: "leads", label: "Лиды", shortLabel: "Лиды", icon: "◎" },
            { key: "deals", label: "Сделки", shortLabel: "Сделки", icon: "◔" },
            { key: "contacts", label: "Контакты", shortLabel: "Контакты", icon: "◉" },
            { key: "companies", label: "Компании", shortLabel: "Компании", icon: "▣" },
            { key: "communications", label: "Коммуникации", shortLabel: "Связь", icon: "✉" },
            { key: "tasks", label: "Задачи", shortLabel: "Задачи", icon: "✓" },
            { key: "touches", label: "Касания", shortLabel: "Касания", icon: "◌" },
            { key: "telephony", label: "Телефония", shortLabel: "Телефония", icon: "☎" }
          ],
          datasets: {
            leads: [],
            deals: [],
            contacts: [],
            companies: [],
            tasks: [],
            touches: [],
            telephony: [],
            automationDrafts: [],
            automationQueue: [],
            automationMessageDrafts: []
          },
          sectionCollectionState: {
            leads: { loaded: false, next: "", isLoadingMore: false },
            deals: { loaded: false, next: "", isLoadingMore: false },
            contacts: { loaded: false, next: "", isLoadingMore: false },
            companies: { loaded: false, next: "", isLoadingMore: false },
            tasks: { loaded: false, next: "", isLoadingMore: false },
            touches: { loaded: false, next: "", isLoadingMore: false },
          }
        };
      },
      computed: {
        isCommunicationsSection() {
          return this.activeSection === "communications";
        },
        isTelephonySection() {
          return this.activeSection === "telephony";
        },
        currentSectionTitle() {
          const titles = {
            leads: "Все лиды",
            deals: "Все сделки",
            contacts: "Все контакты",
            companies: "Все компании",
            communications: "Коммуникации",
            tasks: "Все задачи",
            touches: "Все касания",
            telephony: "Телефония Novofon"
          };
          return titles[this.activeSection] || "CRM";
        },
        createButtonLabel() {
          const labels = {
            leads: "лид",
            deals: "сделку",
            contacts: "контакт",
            companies: "компанию",
            communications: "коммуникацию",
            tasks: "задачу",
            touches: "касание",
            telephony: "настройку"
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
        companyOptions() {
          return this.datasets.companies.map((company) => ({
            id: company.id,
            name: company.name,
          }));
        },
        ownCompanyOptions() {
          return (this.datasets.companies || [])
            .filter((company) => String(company.companyType || "") === "own")
            .slice()
            .sort((left, right) => String(left.name || "").localeCompare(String(right.name || ""), "ru"));
        },
        dealActGeneratorCurrency() {
          const companyId = this.toIntOrNull(this.forms.deals.companyId) || this.toIntOrNull(this.editingDealItem?.clientId);
          const company = (this.datasets.companies || []).find((item) => String(item.id) === String(companyId)) || null;
          return company?.currency || this.editingDealItem?.currency || "RUB";
        },
        selectedDealDocumentGeneratorContract() {
          const contractId = this.toIntOrNull(this.dealActGeneratorForm.contractId);
          if (!contractId) return null;
          return (this.dealDocumentGeneratorContracts || []).find((item) => String(item.id) === String(contractId)) || null;
        },
        selectedDealDocumentGeneratorHourlyRate() {
          return Number(this.selectedDealDocumentGeneratorContract?.hourlyRate || 0);
        },
        dealDocumentGeneratorMeta() {
          const isEditMode = String(this.dealDocumentGeneratorMode || "create") === "edit";
          if (this.dealDocumentGeneratorType === "invoice") {
            return {
              title: isEditMode ? "Редактирование счета" : "Параметры счета",
              subtitle: isEditMode
                ? "Измените строки счета и сохраните документ. Номер счета будет сохранен."
                : "Выберите собственную организацию и проверьте строки счета перед генерацией.",
              submitLabel: isEditMode ? "Сохранить счет" : "Сгенерировать счет",
              preparingLabel: isEditMode ? "Подготовка редактирования счета..." : "Подготовка счета...",
              endpoint: isEditMode && this.dealDocumentGeneratorTargetDocumentId
                ? `/api/v1/deal-documents/${this.dealDocumentGeneratorTargetDocumentId}/regenerate/`
                : "/api/v1/deal-documents/generate-invoice/",
              successPanelLabel: "Счет",
              emptyItemsMessage: "Добавьте хотя бы одну строку счета.",
              openErrorLabel: "счета",
              generateErrorLabel: isEditMode ? "сохранения счета" : "счета",
            };
          }
          return {
            title: isEditMode ? "Редактирование акта" : "Параметры акта",
            subtitle: isEditMode
              ? "Измените строки акта и сохраните документ. Номер акта будет сохранен."
              : "Выберите собственную организацию и проверьте строки документа перед генерацией.",
            submitLabel: isEditMode ? "Сохранить акт" : "Сгенерировать акт",
            preparingLabel: isEditMode ? "Подготовка редактирования акта..." : "Подготовка акта...",
            endpoint: isEditMode && this.dealDocumentGeneratorTargetDocumentId
              ? `/api/v1/deal-documents/${this.dealDocumentGeneratorTargetDocumentId}/regenerate/`
              : "/api/v1/deal-documents/generate-act/",
            successPanelLabel: "Акт",
            emptyItemsMessage: "Добавьте хотя бы одну строку акта.",
            openErrorLabel: "акта",
            generateErrorLabel: isEditMode ? "сохранения акта" : "акта",
          };
        },
        dealActGeneratorTotal() {
          return (this.dealActGeneratorForm.items || []).reduce((total, item) => {
            return total + (this.parseFlexibleNumber(item.quantity) * this.parseFlexibleNumber(item.price));
          }, 0);
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
        editingTaskItem() {
          const taskId = this.toIntOrNull(this.editingTaskId);
          if (!taskId) return null;
          return (this.datasets.tasks || []).find((task) => String(task.id) === String(taskId)) || null;
        },
        editingLeadItem() {
          const leadId = this.toIntOrNull(this.editingLeadId);
          if (!leadId) return null;
          return (this.datasets.leads || []).find((lead) => String(lead.id) === String(leadId)) || null;
        },
        editingDealItem() {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) return null;
          return (this.datasets.deals || []).find((deal) => String(deal.id) === String(dealId)) || null;
        },
        leadSummaryStatusLabel() {
          const statusId = this.toIntOrNull(this.forms.leads.statusId);
          if (!statusId) return "Не выбран";
          const status = (this.metaOptions.leadStatuses || []).find((item) => String(item.id) === String(statusId));
          return status?.name || this.editingLeadItem?.statusLabel || "Не выбран";
        },
        leadSummarySourceLabel() {
          const sourceId = this.toIntOrNull(this.forms.leads.sourceId);
          if (!sourceId) return "Не выбран";
          const source = (this.metaOptions.leadSources || []).find((item) => String(item.id) === String(sourceId));
          return source?.name || this.editingLeadItem?.sourceName || "Не выбран";
        },
        leadSummaryAssignedToLabel() {
          const assignedToId = this.toIntOrNull(this.forms.leads.assignedToId);
          if (!assignedToId) return "Не назначен";
          const user = (this.metaOptions.users || []).find((item) => String(item.id) === String(assignedToId));
          return user ? (user.full_name || user.username) : (this.editingLeadItem?.assignedToName || "Не назначен");
        },
        leadSummaryLastTouch() {
          const leadId = this.toIntOrNull(this.editingLeadId);
          if (!leadId) return null;
          return this.leadLastTouchByLeadId(leadId);
        },
        leadSummaryNextAction() {
          const leadId = this.toIntOrNull(this.editingLeadId);
          if (!leadId) return null;
          const next = this.leadNextActionSummaryByLeadId(leadId);
          return next?.title || next?.at ? next : null;
        },
        leadTasksForActiveLead() {
          const leadId = this.toIntOrNull(this.editingLeadId);
          if (!leadId) return [];
          return this.sortTasksByListRules(this.leadTasksByLeadId(leadId).slice());
        },
        touchLeadOptions() {
          const companyId = this.toIntOrNull(this.forms.touches.companyId);
          return this.datasets.leads
            .filter((lead) => !companyId || String(lead.clientId || "") === String(companyId))
            .map((lead) => ({ id: lead.id, title: lead.title || lead.name }));
        },
        touchDealOptions() {
          const companyId = this.toIntOrNull(this.forms.touches.companyId);
          return this.datasets.deals
            .filter((deal) => !companyId || String(deal.clientId || "") === String(companyId))
            .map((deal) => ({ id: deal.id, title: deal.title || deal.name }));
        },
        touchContactOptions() {
          const companyId = this.toIntOrNull(this.forms.touches.companyId);
          return this.datasets.contacts
            .filter((contact) => !companyId || String(contact.clientId || "") === String(companyId))
            .map((contact) => ({ id: contact.id, title: contact.fullName || contact.name }));
        },
        touchTaskOptions() {
          return this.datasets.tasks.map((task) => ({ id: task.id, title: task.subject || task.name }));
        },
        selectedTouchChannel() {
          const channelId = this.toIntOrNull(this.forms.touches.channelId);
          if (!channelId) return null;
          return (this.metaOptions.communicationChannels || []).find((item) => String(item.id) === String(channelId)) || null;
        },
        selectedTouchResultOption() {
          const resultOptionId = this.toIntOrNull(this.forms.touches.resultOptionId);
          if (!resultOptionId) return null;
          return (this.metaOptions.touchResults || []).find((item) => String(item.id) === String(resultOptionId)) || null;
        },
        touchAutomationEventType() {
          return this.resolveTouchEventTypeFromParts(
            this.selectedTouchChannel,
            this.forms.touches.direction,
            this.selectedTouchResultOption?.code
          );
        },
        matchedTouchAutomationRule() {
          const eventType = String(this.touchAutomationEventType || "").trim();
          if (!eventType) return null;
          return (this.metaOptions.automationRules || []).find((rule) => String(rule.event_type || "").trim() === eventType) || null;
        },
        matchedTouchAutomationOutcome() {
          const outcomeCode = String(this.matchedTouchAutomationRule?.default_outcome_code || "").trim();
          if (!outcomeCode) return null;
          return (this.metaOptions.touchResults || []).find((item) => String(item.code || "").trim() === outcomeCode) || null;
        },
        matchedTouchAutomationNextStepTemplate() {
          const templateId = this.toIntOrNull(this.matchedTouchAutomationRule?.next_step_template);
          if (!templateId) return null;
          return (this.metaOptions.nextStepTemplates || []).find((item) => String(item.id) === String(templateId)) || null;
        },
        pendingAutomationDrafts() {
          return (this.datasets.automationDrafts || []).filter((item) => String(item.status || "") === "pending");
        },
        pendingAutomationMessageDrafts() {
          return (this.datasets.automationMessageDrafts || []).filter((item) => String(item.status || "") === "pending");
        },
        pendingAutomationQueueItems() {
          return (this.datasets.automationQueue || []).filter((item) => String(item.status || "") === "pending");
        },
        managerNotifications() {
          const messageDraftsByTouchEventKey = new Map();
          (this.pendingAutomationMessageDrafts || []).forEach((draft) => {
            const key = `${this.toIntOrNull(draft.sourceTouchId) || 0}::${String(draft.sourceEventType || "").trim()}`;
            if (!messageDraftsByTouchEventKey.has(key)) {
              messageDraftsByTouchEventKey.set(key, draft);
            }
          });
          const queueNotifications = this.pendingAutomationQueueItems.map((item) => ({
            id: `queue-${item.id}`,
            sourceType: "queue",
            sourceId: item.id,
            queueKind: item.itemKind || "",
            touchId: this.toIntOrNull(item.sourceTouchId),
            sourceTouchSummary: item.sourceTouchSummary || "",
            sourceTouchHappenedAt: item.sourceTouchHappenedAt || "",
            conversationId: this.toIntOrNull(item.conversationId),
            dealId: this.toIntOrNull(item.dealId),
            dealTitle: item.dealTitle || "",
            companyId: this.toIntOrNull(item.clientId),
            companyName: item.clientName || "",
            leadId: this.toIntOrNull(item.leadId),
            leadTitle: item.leadTitle || "",
            contactId: this.toIntOrNull(item.contactId),
            ownerId: this.toIntOrNull(item.ownerId),
            title: item.title || item.summary || "Очередь автоматизации",
            eventType: item.sourceEventType || "",
            happenedAt: item.sourceTouchHappenedAt || item.createdAt || "",
            deadline: item.proposedNextStepAt || "",
            recommendedAction: item.recommendedAction || item.proposedNextStep || "",
            uiPriority: String(item.automationRuleUiPriority || "medium"),
            needsConfirmation: true,
            isDraft: false,
            isPrimaryMessage: !!item.isPrimaryMessage,
            availableActions: Array.isArray(item.availableActions) ? item.availableActions : [],
            messageDraft: messageDraftsByTouchEventKey.get(
              `${this.toIntOrNull(item.sourceTouchId) || 0}::${String(item.sourceEventType || "").trim()}`
            ) || null,
          })).map((item) => ({
            ...item,
            hasMessageDraft: !!item.messageDraft,
            messageDraftId: this.toIntOrNull(item.messageDraft?.id),
            messageDraftTitle: item.messageDraft?.title || item.messageDraft?.messageSubject || "",
            messageDraftText: item.messageDraft?.messageText || "",
          }));
          const queueNextStepKeys = new Set(
            queueNotifications
              .filter((item) => String(item.queueKind || "") === "next_step")
              .map((item) => `${this.toIntOrNull(item.touchId) || 0}::${String(item.eventType || "").trim()}`)
          );
          const filteredQueueNotifications = queueNotifications.filter((item) => {
            if (String(item.queueKind || "") !== "attention") {
              return true;
            }
            const dedupeKey = `${this.toIntOrNull(item.touchId) || 0}::${String(item.eventType || "").trim()}`;
            return !queueNextStepKeys.has(dedupeKey);
          });
          const dedupedQueueNotifications = [];
          const notificationIndexByKey = new Map();
          filteredQueueNotifications.forEach((item) => {
            const dedupeKey = [
              String(item.sourceType || ""),
              String(item.queueKind || ""),
              String(this.toIntOrNull(item.touchId) || this.toIntOrNull(item.sourceId) || 0),
              String(item.eventType || "").trim(),
            ].join("::");
            const existingIndex = notificationIndexByKey.get(dedupeKey);
            if (existingIndex === undefined) {
              notificationIndexByKey.set(dedupeKey, dedupedQueueNotifications.length);
              dedupedQueueNotifications.push({
                ...item,
                availableActions: Array.isArray(item.availableActions) ? [...item.availableActions] : [],
              });
              return;
            }
            const existingItem = dedupedQueueNotifications[existingIndex];
            const mergedActions = [...(existingItem.availableActions || [])];
            (item.availableActions || []).forEach((action) => {
              const actionId = String(action?.id || "").trim();
              if (!actionId || mergedActions.some((entry) => String(entry?.id || "").trim() === actionId)) {
                return;
              }
              mergedActions.push(action);
            });
            const existingTimestamp = this.parseTaskDueTimestamp(existingItem.happenedAt) || 0;
            const currentTimestamp = this.parseTaskDueTimestamp(item.happenedAt) || 0;
            const shouldReplace = currentTimestamp > existingTimestamp || (
              currentTimestamp === existingTimestamp
              && this.toIntOrNull(item.sourceId) > this.toIntOrNull(existingItem.sourceId)
            );
            dedupedQueueNotifications[existingIndex] = {
              ...(shouldReplace ? item : existingItem),
              availableActions: mergedActions,
              messageDraft: existingItem.messageDraft || item.messageDraft,
              hasMessageDraft: !!(existingItem.messageDraft || item.messageDraft),
              messageDraftId: this.toIntOrNull(existingItem.messageDraftId || item.messageDraftId),
              messageDraftTitle: existingItem.messageDraftTitle || item.messageDraftTitle || "",
              messageDraftText: existingItem.messageDraftText || item.messageDraftText || "",
            };
          });
          const notifications = [...dedupedQueueNotifications];

          notifications.sort((left, right) => {
            const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
            const leftRank = priorityOrder[left.uiPriority] ?? 99;
            const rightRank = priorityOrder[right.uiPriority] ?? 99;
            if (leftRank !== rightRank) return leftRank - rightRank;
            return (this.parseTaskDueTimestamp(right.happenedAt) || 0) - (this.parseTaskDueTimestamp(left.happenedAt) || 0);
          });
          return notifications;
        },
        managerNotificationsCount() {
          return this.managerNotifications.length;
        },
        activeManagerNotification() {
          const notificationId = String(this.activeManagerNotificationId || "").trim();
          if (!notificationId) return null;
          return (this.managerNotifications || []).find((item) => String(item.id) === notificationId) || null;
        },
        activeUnboundConversation() {
          const conversationId = this.toIntOrNull(this.activeUnboundConversationId);
          if (!conversationId) return null;
          return (this.unboundConversations || []).find((item) => String(item.id) === String(conversationId)) || null;
        },
        unboundConversationCompanyOptions() {
          return this.companyOptions;
        },
        unboundConversationContactOptions() {
          const companyId = this.toIntOrNull(this.unboundConversationBindForm.clientId);
          if (!companyId) return [];
          return (this.datasets.contacts || [])
            .filter((contact) => String(contact.clientId || "") === String(companyId))
            .map((contact) => ({
              id: this.toIntOrNull(contact.id),
              title: contact.fullName || contact.name || contact.email || `Контакт #${contact.id}`,
            }));
        },
        unboundConversationDealOptions() {
          const companyId = this.toIntOrNull(this.unboundConversationBindForm.clientId);
          if (!companyId) return [];
          return (this.datasets.deals || [])
            .filter((deal) => String(deal.clientId || "") === String(companyId))
            .map((deal) => ({
              id: this.toIntOrNull(deal.id),
              title: deal.title || deal.name || `Сделка #${deal.id}`,
              isActive: this.isDealOpen(deal.stageStatus),
            }))
            .sort((left, right) => (left.isActive === right.isActive ? 0 : (left.isActive ? -1 : 1)));
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
        dealSummaryContact() {
          const companyId = this.toIntOrNull(this.forms.deals.companyId);
          if (!companyId) return null;
          const contacts = (this.dealCompanyContacts.length ? this.dealCompanyContacts : this.datasets.contacts)
            .filter((contact) => String(contact.clientId || "") === String(companyId));
          return contacts.find((contact) => contact.isPrimary) || contacts[0] || null;
        },
        activeLeadPhoneCallHistoryState() {
          return this.getPhoneCallHistoryEntityState("lead", this.editingLeadId, false) || this.defaultPhoneCallHistoryState();
        },
        activeDealPhoneCallHistoryState() {
          return this.getPhoneCallHistoryEntityState("deal", this.editingDealId, false) || this.defaultPhoneCallHistoryState();
        },
        activeContactPhoneCallHistoryState() {
          return this.getPhoneCallHistoryEntityState("contact", this.editingContactId, false) || this.defaultPhoneCallHistoryState();
        },
        activeCompanyPhoneCallHistoryState() {
          return this.getPhoneCallHistoryEntityState("company", this.editingCompanyId, false) || this.defaultPhoneCallHistoryState();
        },
        dealCommunicationContactOptions() {
          const companyId = this.toIntOrNull(this.forms.deals.companyId);
          if (!companyId) return [];
          const contacts = (this.dealCompanyContacts.length ? this.dealCompanyContacts : this.datasets.contacts)
            .filter((contact) => String(contact.clientId || "") === String(companyId));
          return contacts.map((contact) => ({
            id: this.toIntOrNull(contact.id),
            title: contact.fullName || contact.name || contact.email || `Контакт #${contact.id}`,
            email: contact.email || "",
            telegram: contact.telegram || "",
          }));
        },
        dealDocumentSendEmailConversations() {
          return (this.dealDocumentSendConversations || []).filter((item) => String(item.channel || "").trim().toLowerCase() === "email");
        },
        activeDealDocumentSendConversation() {
          const conversationId = this.toIntOrNull(this.activeDealDocumentSendConversationId);
          if (!conversationId) return null;
          return (this.dealDocumentSendEmailConversations || []).find((item) => String(item.id) === String(conversationId)) || null;
        },
        dealDocumentSendDisplayName() {
          return this.documentDisplayName(this.dealDocumentSendTarget?.originalName || "", "");
        },
        dealDocumentSendAttachmentName() {
          const originalName = String(this.dealDocumentSendTarget?.originalName || "").trim();
          if (!originalName) {
            return "document.pdf";
          }
          const extensionIndex = originalName.lastIndexOf(".");
          if (extensionIndex <= 0) {
            return `${originalName}.pdf`;
          }
          return `${originalName.slice(0, extensionIndex)}.pdf`;
        },
        dealSummaryTouches() {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) return [];
          return (this.datasets.touches || []).filter((touch) => String(touch.dealId || "") === String(dealId));
        },
        dealSummaryUpcomingTasks() {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) return [];
          return (this.datasets.tasks || [])
            .filter((task) => (
              String(task.dealId || "") === String(dealId)
              && this.isTaskActiveStatus(task.taskStatus || task.status)
              && task.dueAtRaw
            ))
            .slice()
            .sort((left, right) => (
              (this.taskItemSatisfiesDealNextStepRequirement(left) ? 0 : 1) - (this.taskItemSatisfiesDealNextStepRequirement(right) ? 0 : 1)
              || (this.parseTaskDueTimestamp(left.dueAtRaw) || 0) - (this.parseTaskDueTimestamp(right.dueAtRaw) || 0)
            ));
        },
        dealSummaryNextStepTask() {
          return this.dealSummaryUpcomingTasks[0] || null;
        },
        dealSummaryNextStepLabel() {
          return this.dealSummaryNextStepTask?.subject || this.dealSummaryNextTouch?.nextStep || "Не указан";
        },
        dealSummaryNextStepAtLabel() {
          if (this.dealSummaryNextStepTask?.dueAtRaw) {
            return this.formatDueLabel(this.dealSummaryNextStepTask.dueAtRaw);
          }
          if (this.dealSummaryNextTouch?.nextStepAtRaw) {
            return this.formatDueLabel(this.dealSummaryNextTouch.nextStepAtRaw);
          }
          return "Не указана";
        },
        dealSummaryLastTouch() {
          const touches = this.dealSummaryTouches.slice();
          touches.sort((left, right) => (this.parseTaskDueTimestamp(right.happenedAtRaw) || 0) - (this.parseTaskDueTimestamp(left.happenedAtRaw) || 0));
          return touches[0] || null;
        },
        dealSummaryOverdueTasksLabel() {
          const overdueCount = (this.dealTasksForActiveDeal || []).filter((task) => this.isTaskOverdue(task.dueAtRaw, task.taskStatus)).length;
          if (!overdueCount) {
            return "Нет просроченных задач";
          }
          return overdueCount === 1 ? "1 просроченная задача" : `${overdueCount} просроченных задач`;
        },
        dealSummaryNextTouch() {
          const touches = this.dealSummaryTouches
            .filter((touch) => touch.nextStepAtRaw)
            .slice();
          touches.sort((left, right) => (this.parseTaskDueTimestamp(left.nextStepAtRaw) || 0) - (this.parseTaskDueTimestamp(right.nextStepAtRaw) || 0));
          return touches[0] || null;
        },
        dealActivityStatusLabel() {
          const nextTouch = this.dealSummaryNextTouch;
          const nextStepAt = this.parseTaskDueTimestamp(nextTouch?.nextStepAtRaw);
          if (nextStepAt !== null) {
            return nextStepAt < Date.now() ? "Просрочено" : "В срок";
          }
          const lastTouch = this.dealSummaryLastTouch;
          const happenedAt = this.parseTaskDueTimestamp(lastTouch?.happenedAtRaw);
          if (happenedAt !== null) {
            const daysWithoutContact = Math.max(0, Math.floor((Date.now() - happenedAt) / 86400000));
            return `Без контакта ${daysWithoutContact} дн`;
          }
          return "Без контакта";
        },
        dealSummaryOwnerLabel() {
          const ownerId = this.toIntOrNull(this.forms.deals.ownerId);
          if (!ownerId) {
            return this.editingDealItem?.ownerName || "Не назначен";
          }
          const user = (this.metaOptions.users || []).find((item) => String(item.id) === String(ownerId));
          return user ? (user.full_name || user.username) : (this.editingDealItem?.ownerName || "Не назначен");
        },
        dealAutomationTouchItems() {
          return this.dealSummaryTouches
            .map((touch) => this.buildAutomationTouchEntry(touch))
            .filter(Boolean)
            .filter((item) => (
              item.rule?.show_in_summary
              || item.uiMode !== "history_only"
              || item.needsAttention
              || item.isDraft
            ))
            .sort((left, right) => this.compareAutomationEntries(left, right));
        },
        dealAttentionItems() {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) return [];
          return this.pendingAutomationQueueItems
            .filter((item) => String(item.dealId || "") === String(dealId) && String(item.itemKind || "") === "attention")
            .map((item) => this.buildAutomationQueueEntry(item))
            .filter(Boolean);
        },
        dealAttentionChains() {
          return this.groupAutomationEntries(this.dealAttentionItems);
        },
        dealSignalItems() {
          return this.dealAutomationTouchItems.filter((item) => item.uiMode === "signal");
        },
        dealSignalChains() {
          return this.groupAutomationEntries(this.dealSignalItems);
        },
        dealDraftTouchItems() {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) return [];
          const draftItems = this.pendingAutomationDrafts
            .filter((item) => String(item.dealId || "") === String(dealId))
            .map((item) => this.buildAutomationDraftEntry(item))
            .filter(Boolean);
          const messageDraftItems = this.pendingAutomationMessageDrafts
            .filter((item) => String(item.dealId || "") === String(dealId))
            .map((item) => this.buildAutomationMessageDraftEntry(item))
            .filter(Boolean);
          return [...draftItems, ...messageDraftItems];
        },
        dealNextStepQueueItems() {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) return [];
          return this.pendingAutomationQueueItems
            .filter((item) => String(item.dealId || "") === String(dealId) && String(item.itemKind || "") === "next_step")
            .map((item) => this.buildAutomationQueueEntry(item))
            .filter(Boolean);
        },
        dealDraftTouchChains() {
          return this.groupAutomationEntries(this.dealDraftTouchItems);
        },
        dealLatestSignificantItem() {
          const items = this.dealAutomationTouchItems
            .filter((item) => item.isSignificant)
            .slice()
            .sort((left, right) => (
              (this.parseTaskDueTimestamp(right.happenedAtRaw) || 0) - (this.parseTaskDueTimestamp(left.happenedAtRaw) || 0)
              || this.compareAutomationEntries(left, right)
            ));
          return items[0] || null;
        },
        dealAutomationNextAction() {
          const nextStepQueueItem = this.dealNextStepQueueItems
            .filter((item) => item.hasSuggestedNextStep)
            .slice()
            .sort((left, right) => {
              const leftAt = this.parseTaskDueTimestamp(left.suggestedNextStepAt || left.happenedAtRaw) || Number.MAX_SAFE_INTEGER;
              const rightAt = this.parseTaskDueTimestamp(right.suggestedNextStepAt || right.happenedAtRaw) || Number.MAX_SAFE_INTEGER;
              return leftAt - rightAt || this.compareAutomationEntries(left, right);
            })[0];
          if (nextStepQueueItem) {
            return {
              kind: "automation_queue",
              title: nextStepQueueItem.suggestedNextStep || nextStepQueueItem.recommendedAction || "Не указан",
              at: nextStepQueueItem.suggestedNextStepAt || null,
              ownerName: nextStepQueueItem.ownerName || this.dealSummaryOwnerLabel,
              sourceLabel: `по автоматизации · ${nextStepQueueItem.eventLabel}`,
              sourceTouchId: nextStepQueueItem.touchId,
              recommendedAction: nextStepQueueItem.recommendedAction || "",
              canConfirm: true,
              canCreateTask: false,
              queueId: nextStepQueueItem.queueId,
            };
          }

          const nextStepDraft = this.dealDraftTouchItems
            .filter((item) => item.draftKind === "next_step" && item.hasSuggestedNextStep)
            .slice()
            .sort((left, right) => {
              const leftAt = this.parseTaskDueTimestamp(left.suggestedNextStepAt || left.happenedAtRaw) || Number.MAX_SAFE_INTEGER;
              const rightAt = this.parseTaskDueTimestamp(right.suggestedNextStepAt || right.happenedAtRaw) || Number.MAX_SAFE_INTEGER;
              return leftAt - rightAt || this.compareAutomationEntries(left, right);
            })[0];
          if (nextStepDraft) {
            return {
              kind: "automation_draft",
              title: nextStepDraft.suggestedNextStep || "Не указан",
              at: nextStepDraft.suggestedNextStepAt || null,
              ownerName: nextStepDraft.ownerName || this.dealSummaryOwnerLabel,
              sourceLabel: `черновик · ${nextStepDraft.eventLabel}`,
              sourceTouchId: nextStepDraft.touchId,
              recommendedAction: nextStepDraft.recommendedAction || "",
              canCreateTask: false,
            };
          }
          const nextTask = this.dealSummaryNextStepTask;
          if (nextTask) {
            const relatedTouch = this.toIntOrNull(nextTask.relatedTouchId)
              ? (this.datasets.touches || []).find((touch) => String(touch.id) === String(nextTask.relatedTouchId))
              : null;
            const relatedTouchEntry = relatedTouch ? this.buildAutomationTouchEntry(relatedTouch) : null;
            return {
              kind: "task",
              title: nextTask.subject || nextTask.name || "Не указан",
              at: nextTask.dueAtRaw || null,
              ownerName: relatedTouchEntry?.ownerName || this.dealSummaryOwnerLabel,
              sourceLabel: relatedTouchEntry ? `по автоматизации · ${relatedTouchEntry.eventLabel}` : "вручную",
              sourceTouchId: this.toIntOrNull(nextTask.relatedTouchId),
              recommendedAction: relatedTouchEntry?.recommendedAction || "",
              canCreateTask: false,
            };
          }

          const automationPrompt = this.dealAutomationTouchItems
            .filter((item) => item.hasSuggestedNextStep)
            .slice()
            .sort((left, right) => {
              const leftAt = this.parseTaskDueTimestamp(left.suggestedNextStepAt || left.happenedAtRaw) || Number.MAX_SAFE_INTEGER;
              const rightAt = this.parseTaskDueTimestamp(right.suggestedNextStepAt || right.happenedAtRaw) || Number.MAX_SAFE_INTEGER;
              return leftAt - rightAt || this.compareAutomationEntries(left, right);
            })[0];
          if (automationPrompt) {
            return {
              kind: "automation",
              title: automationPrompt.suggestedNextStep || "Не указан",
              at: automationPrompt.suggestedNextStepAt || null,
              ownerName: automationPrompt.ownerName || this.dealSummaryOwnerLabel,
              sourceLabel: `по автоматизации · ${automationPrompt.eventLabel}`,
              sourceTouchId: automationPrompt.touchId,
              recommendedAction: automationPrompt.recommendedAction || "",
              canCreateTask: true,
              touchId: automationPrompt.touchId,
              defaultTaskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: !!automationPrompt.touch?.channelId,
                requiresFollowUp: !automationPrompt.touch?.channelId,
                satisfiesDealNextStepRequirement: !!automationPrompt.touch?.channelId,
              }),
              communicationChannelId: automationPrompt.touch?.channelId || null,
            };
          }

          const nextTouch = this.dealSummaryNextTouch;
          if (nextTouch) {
            return {
              kind: "touch",
              title: nextTouch.nextStep || nextTouch.summary || nextTouch.resultOptionName || "Не указан",
              at: nextTouch.nextStepAtRaw || null,
              ownerName: nextTouch.ownerName || this.dealSummaryOwnerLabel,
              sourceLabel: "вручную",
              sourceTouchId: this.toIntOrNull(nextTouch.id),
              recommendedAction: "",
              canCreateTask: !!String(nextTouch.nextStep || "").trim(),
              touchId: this.toIntOrNull(nextTouch.id),
              defaultTaskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: !!nextTouch.channelId,
                requiresFollowUp: !nextTouch.channelId,
                satisfiesDealNextStepRequirement: !!nextTouch.channelId,
              }),
              communicationChannelId: nextTouch.channelId || null,
            };
          }

          return null;
        },
        hasDealAutomationSummaryBlocks() {
          return !!(
            this.dealAutomationNextAction
            || this.dealLatestSignificantItem
            || this.dealAttentionChains.length
            || this.dealSignalChains.length
            || this.dealDraftTouchChains.length
          );
        },
        parsedDealEventItems() {
          return this.parseEventLog(this.forms.deals.events);
        },
        filteredDealEventItems() {
          return this.filterTimelineItems("deals", this.parsedDealEventItems);
        },
        dealTimelineItems() {
          return this.groupDealTimelineEvents(this.filteredDealEventItems);
        },
        parsedLeadEventItems() {
          return this.parseEventLog(this.leadEventLog(this.forms.leads));
        },
        filteredLeadEventItems() {
          return this.filterTimelineItems("leads", this.parsedLeadEventItems);
        },
        leadTimelineItems() {
          return this.groupDealTimelineEvents(this.filteredLeadEventItems);
        },
        parsedCompanyEventItems() {
          return this.parseEventLog(this.forms.companies.events);
        },
        filteredCompanyEventItems() {
          return this.filterTimelineItems("companies", this.parsedCompanyEventItems);
        },
        companyTimelineItems() {
          return this.groupDealTimelineEvents(this.filteredCompanyEventItems);
        },
        companySummaryDeals() {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) return [];
          return (this.datasets.deals || []).filter((deal) => String(deal.clientId || "") === String(companyId));
        },
        companySummaryLeads() {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) return [];
          return (this.datasets.leads || []).filter((lead) => String(lead.clientId || "") === String(companyId));
        },
        companySummaryActiveLeads() {
          const activeCodes = new Set(["new", "in_progress", "attempting_contact", "qualified"]);
          return this.companySummaryLeads.filter((lead) => activeCodes.has(String(lead.statusCode || lead.status || "").trim()));
        },
        companySummaryConvertedLeads() {
          return this.companySummaryLeads.filter((lead) => {
            const statusCode = String(lead.statusCode || lead.status || "").trim();
            return statusCode === "converted" || !!this.leadConvertedDealByLeadId(lead.id);
          });
        },
        companySummaryClosedLeads() {
          const closedCodes = new Set(["lost", "unqualified", "spam", "archived"]);
          return this.companySummaryLeads.filter((lead) => {
            const statusCode = String(lead.statusCode || lead.status || "").trim();
            return closedCodes.has(statusCode) && !this.leadConvertedDealByLeadId(lead.id);
          });
        },
        companySummaryActiveDeals() {
          return this.companySummaryDeals.filter((deal) => this.getDealStatusBucket(deal) !== "done");
        },
        companySummaryWonDeals() {
          return this.companySummaryDeals.filter((deal) => {
            const stageCode = String(deal.stageCode || "").trim().toLowerCase();
            return !!deal.isWon || stageCode === "won";
          });
        },
        companySummaryFailedDeals() {
          return this.companySummaryDeals.filter((deal) => {
            const stageCode = String(deal.stageCode || "").trim().toLowerCase();
            return stageCode === "failed";
          });
        },
        companySummaryTouches() {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) return [];
          return (this.datasets.touches || []).filter((touch) => String(touch.clientId || "") === String(companyId));
        },
        companySummaryTasks() {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) return [];
          return (this.datasets.tasks || []).filter((task) => String(task.clientId || "") === String(companyId));
        },
        companySummaryLastTouch() {
          const touches = this.companySummaryTouches.slice();
          touches.sort((left, right) => (this.parseTaskDueTimestamp(right.happenedAtRaw) || 0) - (this.parseTaskDueTimestamp(left.happenedAtRaw) || 0));
          return touches[0] || null;
        },
        companySummaryNextTouch() {
          const now = Date.now();
          const touches = this.companySummaryTouches
            .filter((touch) => {
              const ts = this.parseTaskDueTimestamp(touch.nextStepAtRaw);
              return ts !== null && ts >= now;
            })
            .slice();
          touches.sort((left, right) => (this.parseTaskDueTimestamp(left.nextStepAtRaw) || 0) - (this.parseTaskDueTimestamp(right.nextStepAtRaw) || 0));
          return touches[0] || null;
        },
        companySummaryNextTask() {
          const now = Date.now();
          const tasks = this.companySummaryTasks
            .filter((task) => this.isTaskActiveStatus(task.taskStatus || task.status))
            .filter((task) => {
              const ts = this.parseTaskDueTimestamp(task.dueAtRaw);
              return ts !== null && ts >= now;
            })
            .slice();
          tasks.sort((left, right) => (this.parseTaskDueTimestamp(left.dueAtRaw) || 0) - (this.parseTaskDueTimestamp(right.dueAtRaw) || 0));
          return tasks[0] || null;
        },
        companySummaryNextAction() {
          const nextTask = this.companySummaryNextTask;
          const nextTouch = this.companySummaryNextTouch;
          const nextTaskTs = this.parseTaskDueTimestamp(nextTask?.dueAtRaw);
          const nextTouchTs = this.parseTaskDueTimestamp(nextTouch?.nextStepAtRaw);
          if (nextTaskTs !== null && nextTouchTs !== null) {
            return nextTaskTs <= nextTouchTs
              ? { type: "task", item: nextTask, at: nextTask.dueAtRaw }
              : { type: "touch", item: nextTouch, at: nextTouch.nextStepAtRaw };
          }
          if (nextTaskTs !== null) {
            return { type: "task", item: nextTask, at: nextTask.dueAtRaw };
          }
          if (nextTouchTs !== null) {
            return { type: "touch", item: nextTouch, at: nextTouch.nextStepAtRaw };
          }
          return null;
        },
        companySummaryCurrentDeal() {
          const deals = this.companySummaryActiveDeals.slice();
          deals.sort((left, right) => {
            const leftTs = this.parseTaskDueTimestamp(left.closeDate) || Number.MAX_SAFE_INTEGER;
            const rightTs = this.parseTaskDueTimestamp(right.closeDate) || Number.MAX_SAFE_INTEGER;
            return leftTs - rightTs || Number(left.id || 0) - Number(right.id || 0);
          });
          return deals[0] || null;
        },
        companySummaryOpenAmount() {
          return this.companySummaryActiveDeals.reduce((sum, deal) => {
            const numeric = Number(deal.amount || 0);
            return sum + (Number.isFinite(numeric) ? numeric : 0);
          }, 0);
        },
        companySummaryWonAmount() {
          return this.companySummaryWonDeals.reduce((sum, deal) => {
            const numeric = Number(deal.amount || 0);
            return sum + (Number.isFinite(numeric) ? numeric : 0);
          }, 0);
        },
        companySummaryResponsibleLabel() {
          const currentDealOwner = this.companySummaryCurrentDeal?.ownerName;
          if (currentDealOwner) {
            return currentDealOwner;
          }
          const activeDealWithOwner = this.companySummaryActiveDeals.find((deal) => String(deal.ownerName || "").trim());
          if (activeDealWithOwner) {
            return activeDealWithOwner.ownerName;
          }
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) return "Не назначен";
          const leadWithOwner = (this.datasets.leads || []).find((lead) => (
            String(lead.clientId || "") === String(companyId) && String(lead.assignedToName || "").trim()
          ));
          return leadWithOwner?.assignedToName || "Не назначен";
        },
        companySummaryFirstSourceLabel() {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) return "Не указан";
          const leadCandidates = (this.datasets.leads || [])
            .filter((lead) => String(lead.clientId || "") === String(companyId) && String(lead.sourceName || "").trim())
            .sort((left, right) => Number(left.id || 0) - Number(right.id || 0));
          if (leadCandidates.length) {
            return leadCandidates[0].sourceName;
          }
          const dealCandidates = this.companySummaryDeals
            .filter((deal) => String(deal.sourceName || "").trim())
            .sort((left, right) => Number(left.id || 0) - Number(right.id || 0));
          return dealCandidates[0]?.sourceName || "Не указан";
        },
        companySummaryRegionLabel() {
          return this.resolveCompanyRegionLabel(this.forms.companies.address);
        },
        companySummarySegmentLabel() {
          return "Не указан";
        },
        companySummaryStatusLabel() {
          return this.forms.companies.isActive ? "Активный" : "Неактивный";
        },
        isDealFailedStageSelected() {
          return this.resolveDealStageCode(this.forms.deals.stageId) === "failed";
        },
        canSubmitDealCompanyAction() {
          return !!this.dealCompanyForm.name.trim();
        },
        shouldShowCompanyField() {
          return (fieldKeyOrValue, maybeValue) => {
            const fieldKey = maybeValue === undefined ? null : fieldKeyOrValue;
            const value = maybeValue === undefined ? fieldKeyOrValue : maybeValue;
            return this.isCreatingCompany
              || (!!fieldKey ? this.isOptionalFieldExpanded("companies", fieldKey) : !!this.editingCompanyId)
              || this.hasVisibleFieldValue(value);
          };
        },
        shouldShowLeadField() {
          return (fieldKeyOrValue, maybeValue) => {
            const fieldKey = maybeValue === undefined ? null : fieldKeyOrValue;
            const value = maybeValue === undefined ? fieldKeyOrValue : maybeValue;
            return this.isCreatingLead
              || (!!fieldKey && this.isOptionalFieldExpanded("leads", fieldKey))
              || this.hasVisibleFieldValue(value);
          };
        },
        shouldShowDealField() {
          return (fieldKeyOrValue, maybeValue) => {
            const fieldKey = maybeValue === undefined ? null : fieldKeyOrValue;
            const value = maybeValue === undefined ? fieldKeyOrValue : maybeValue;
            return this.isCreatingDeal
              || (!!fieldKey ? this.isOptionalFieldExpanded("deals", fieldKey) : !!this.editingDealId)
              || this.hasVisibleFieldValue(value);
          };
        },
        shouldShowTaskField() {
          return (fieldKeyOrValue, maybeValue) => {
            const fieldKey = maybeValue === undefined ? null : fieldKeyOrValue;
            const value = maybeValue === undefined ? fieldKeyOrValue : maybeValue;
            return this.isCreatingTask
              || (!!fieldKey && this.isOptionalFieldExpanded("tasks", fieldKey))
              || this.hasVisibleFieldValue(value);
          };
        },
        showTaskTypeSelector() {
          return this.isOptionalFieldExpanded("tasks", "taskCategoryId")
            || !!this.toIntOrNull(this.forms.tasks.taskCategoryId)
            || !!this.toIntOrNull(this.forms.tasks.taskTypeId);
        },
        showTaskCommunicationChannelField() {
          return this.taskFormUsesCommunicationChannel(this.forms.tasks);
        },
        filteredTaskDealOptions() {
          const companyId = this.toIntOrNull(this.forms.tasks.companyId);
          const deals = Array.isArray(this.datasets.deals) ? this.datasets.deals : [];
          if (!companyId) {
            return [];
          }
          return deals.filter((deal) => String(deal.clientId || "") === String(companyId));
        },
        taskLeadOptions() {
          return (this.datasets.leads || [])
            .slice()
            .sort((left, right) => String(left.title || left.name || "").localeCompare(String(right.title || right.name || ""), "ru"))
            .map((lead) => ({
              id: lead.id,
              title: lead.title || lead.name || `Лид #${lead.id}`,
            }));
        },
        showTaskDealSelector() {
          return !!this.toIntOrNull(this.forms.tasks.companyId)
            || !!this.toIntOrNull(this.forms.tasks.dealId)
            || this.isOptionalFieldExpanded("tasks", "dealId");
        },
        shouldShowLeadTrackingBlock() {
          return this.isCreatingLead
            || !!this.forms.leads.websiteSessionId
            || this.forms.leads.sourceNames.length > 0
            || this.forms.leads.history.length > 0
            || !!String(this.forms.leads.events || "").trim();
        },
        showTaskResultField() {
          return this.isTaskDoneStatus(this.forms.tasks.status) || !!String(this.forms.tasks.result || "").trim();
        },
        taskSummaryStatusLabel() {
          return this.taskStatusMeta(this.forms.tasks.status).label || "Не выбран";
        },
        taskSummaryPriorityLabel() {
          const value = String(this.forms.tasks.priority || "").trim();
          return (this.taskPriorityOptions || []).find((option) => option.value === value)?.label || "Не выбран";
        },
        taskSummaryOwnerLabel() {
          const ownerId = this.toIntOrNull(this.forms.tasks.ownerId);
          if (!ownerId) return "Не назначен";
          const user = (this.metaOptions.users || []).find((item) => String(item.id) === String(ownerId));
          return user ? (user.full_name || user.username) : (this.editingTaskItem?.ownerName || "Не назначен");
        },
        taskSummaryTaskCategoryLabel() {
          const category = this.resolveTaskCategoryById(this.forms.tasks.taskCategoryId);
          return category?.name || "Не выбрана";
        },
        taskSummaryTaskTypeLabel() {
          const taskType = this.resolveTaskTypeById(this.forms.tasks.taskTypeId);
          return taskType?.name || "Не выбран";
        },
        taskSummaryLeadLabel() {
          const leadId = this.toIntOrNull(this.forms.tasks.leadId);
          if (!leadId) return "Не выбран";
          return (this.datasets.leads || []).find((lead) => String(lead.id) === String(leadId))?.title || "Не выбран";
        },
        taskSummaryCompanyLabel() {
          const companyId = this.toIntOrNull(this.forms.tasks.companyId);
          if (!companyId) return "Не выбрана";
          return (this.datasets.companies || []).find((company) => String(company.id) === String(companyId))?.name || "Не выбрана";
        },
        taskSummaryDealLabel() {
          const dealId = this.toIntOrNull(this.forms.tasks.dealId);
          if (!dealId) return "Не выбрана";
          return (this.datasets.deals || []).find((deal) => String(deal.id) === String(dealId))?.title || "Не выбрана";
        },
        taskSummaryDueLabel() {
          return this.forms.tasks.dueAt ? this.formatDueLabel(this.forms.tasks.dueAt) : "Не указан";
        },
        taskSummaryReminderLabel() {
          const normalizedValue = Number(this.forms.tasks.reminderOffsetMinutes || 30);
          return (this.taskReminderOptions || []).find((option) => Number(option.value) === normalizedValue)?.label || `${normalizedValue} мин`;
        },
        currentTaskTypeHasAutomaticFollowUp() {
          const taskType = this.resolveTaskTypeById(this.forms.tasks.taskTypeId);
          return !!(taskType && taskType.auto_task_on_done && this.toIntOrNull(taskType.auto_task_type));
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
          return !!this.editingTaskId
            && this.isTaskDoneStatus(this.forms.tasks.status)
            && !this.currentTaskTypeHasAutomaticFollowUp
            && (
              this.taskFormRequiresFollowUp(this.forms.tasks)
              || this.taskActiveDealRequiresFollowUp
            );
        },
        taskFollowUpDealTitle() {
          if (this.taskActiveDeal) {
            return this.taskActiveDeal.title || this.taskActiveDeal.name;
          }
          const companyId = this.toIntOrNull(this.forms.tasks.companyId);
          if (companyId) {
            const company = this.datasets.companies.find((item) => String(item.id) === String(companyId));
            if (company) {
              return company.name || `Компания #${companyId}`;
            }
          }
          return "Без сделки";
        },
        filteredTaskFollowUpTypeOptions() {
          return this.filterTaskTypesByCategory(this.taskFollowUpForm.taskCategoryId);
        },
        filteredTaskFollowUpCategoryOptions() {
          return this.filterTaskCategories();
        },
        showTaskFollowUpTypeSelector() {
          return !!this.toIntOrNull(this.taskFollowUpForm.taskCategoryId)
            || !!this.toIntOrNull(this.taskFollowUpForm.taskTypeId);
        },
        showTaskFollowUpCommunicationChannelField() {
          return this.taskFormUsesCommunicationChannel(this.taskFollowUpForm);
        },
        filteredDealTaskTypeOptions() {
          return this.filterTaskTypesByCategory(this.dealTaskForm.taskCategoryId);
        },
        filteredDealTaskCategoryOptions() {
          return this.filterTaskCategories();
        },
        showDealTaskTypeSelector() {
          return !!this.toIntOrNull(this.dealTaskForm.taskCategoryId)
            || !!this.toIntOrNull(this.dealTaskForm.taskTypeId);
        },
        showDealTaskCommunicationChannelField() {
          return this.taskFormUsesCommunicationChannel(this.dealTaskForm);
        },
        filteredTouchFollowUpTypeOptions() {
          return this.filterTaskTypesByCategory(this.touchFollowUpForm.taskCategoryId);
        },
        filteredTouchFollowUpCategoryOptions() {
          return this.filterTaskCategories();
        },
        showTouchFollowUpTypeSelector() {
          return !!this.toIntOrNull(this.touchFollowUpForm.taskCategoryId)
            || !!this.toIntOrNull(this.touchFollowUpForm.taskTypeId);
        },
        showTouchFollowUpCommunicationChannelField() {
          return this.taskFormUsesCommunicationChannel(this.touchFollowUpForm);
        },
        emptyLabel() {
          const labels = {
            leads: "лидов",
            deals: "сделок",
            contacts: "контактов",
            companies: "компаний",
            communications: "коммуникаций",
            tasks: "задач",
            telephony: "настроек"
          };
          return labels[this.activeSection] || "элементов";
        },
        emptySuffix() {
          return this.activeSection === "contacts" ? "о" : "";
        },
        currentItems() {
          if (this.isTelephonySection || this.isCommunicationsSection) {
            return [];
          }
          return this.datasets[this.activeSection] || [];
        },
        activeSectionCollectionState() {
          return this.sectionCollectionState?.[this.activeSection] || { loaded: false, next: "", isLoadingMore: false };
        },
        telephonyUserOptions() {
          return (this.metaOptions.users || [])
            .filter((user) => user && user.id)
            .map((user) => ({
              id: Number.parseInt(user.id, 10) || null,
              label: user.full_name || user.username || `Пользователь #${user.id}`,
            }))
            .filter((user) => user.id);
        },
        telephonyConnectionStatusLabel() {
          const status = String(this.telephonySettings.lastConnectionStatus || "").trim().toLowerCase();
          if (status === "ok") return "Подключение проверено";
          if (status === "error") return "Ошибка подключения";
          return "Проверка не запускалась";
        },
        telephonyConnectionStatusClass() {
          const status = String(this.telephonySettings.lastConnectionStatus || "").trim().toLowerCase();
          if (status === "ok") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
          if (status === "error") return "border-red-400/30 bg-red-400/10 text-red-200";
          return "border-crm-border bg-[#123753] text-crm-text";
        },
        telephonyActiveMappingsCount() {
          return (this.telephonySettings.mappings || []).filter((item) => item.isActive).length;
        },
        communicationsOwnedCompanyIds() {
          if (this.currentUserCanViewAllCommunications) {
            return null;
          }
          const companyIds = new Set();
          (this.communicationsDeals || []).forEach((deal) => {
            if (String(this.toIntOrNull(deal.ownerId) || "") !== String(this.currentUserId || "")) {
              return;
            }
            const companyId = this.toIntOrNull(deal.clientId);
            if (companyId) {
              companyIds.add(companyId);
            }
          });
          return companyIds;
        },
        communicationsVisibleCompanies() {
          const q = String(this.search || "").trim().toLowerCase();
          const ownedIds = this.communicationsOwnedCompanyIds;
          return (this.communicationsCompanies || [])
            .filter((company) => String(company.companyType || "client").trim() === "client")
            .filter((company) => (
              ownedIds === null
              || ownedIds.has(this.toIntOrNull(company.id))
            ))
            .filter((company) => {
              if (!q) return true;
              const haystack = [
                company.name,
                company.phone,
                company.email,
                company.inn,
                company.legalName,
              ].join(" ").toLowerCase();
              return haystack.includes(q);
            })
            .slice()
            .sort((left, right) => String(left.name || "").localeCompare(String(right.name || ""), "ru"));
        },
        selectedCommunicationsCompany() {
          const companyId = this.toIntOrNull(this.communicationsSelectedCompanyId);
          if (!companyId) return null;
          return (this.communicationsCompanies || []).find((item) => String(item.id) === String(companyId)) || null;
        },
        communicationsCompanyContactOptions() {
          return (this.communicationsContacts || [])
            .slice()
            .sort((left, right) => (
              (left.isPrimary === right.isPrimary ? 0 : (left.isPrimary ? -1 : 1))
              || String(left.fullName || "").localeCompare(String(right.fullName || ""), "ru")
            ));
        },
        communicationsFilteredTimelineItems() {
          const filterValue = String(this.communicationsTimelineFilter || "all").trim().toLowerCase();
          return [...(this.communicationsMessages || []), ...(this.communicationsCalls || [])]
            .filter((item) => {
              if (filterValue === "all") return true;
              if (filterValue === "calls") return item.timelineType === "call";
              return item.timelineChannel === filterValue;
            })
            .slice()
            .sort((left, right) => (
              (this.parseTaskDueTimestamp(right.timelineAt) || 0) - (this.parseTaskDueTimestamp(left.timelineAt) || 0)
            ));
        },
        selectedCommunicationsTimelineItem() {
          const itemKey = String(this.communicationsSelectedTimelineItemKey || "").trim();
          if (!itemKey) return null;
          return this.communicationsFilteredTimelineItems.find((item) => String(item.timelineKey || "") === itemKey) || null;
        },
        communicationsPendingDocumentName() {
          return this.documentDisplayName(this.communicationsPendingDealDocument?.originalName || "", "");
        },
        communicationsSelectedCompanyPhone() {
          const companyPhone = String(this.selectedCommunicationsCompany?.phone || "").trim();
          if (companyPhone) {
            return companyPhone;
          }
          const primaryContactPhone = (this.communicationsCompanyContactOptions || []).find((item) => String(item.phone || "").trim());
          return String(primaryContactPhone?.phone || "").trim();
        },
        communicationsComposerSelectedContact() {
          const contactId = this.toIntOrNull(this.communicationsComposer.contactId);
          if (!contactId) return null;
          return (this.communicationsCompanyContactOptions || []).find((item) => String(item.id) === String(contactId)) || null;
        },
        activeFilterRows() {
          if (this.isTelephonySection || this.isCommunicationsSection) {
            return [];
          }
          const rows = [];
          if (this.selectedStatusFilters.length) {
            rows.push({
              key: "status",
              fieldLabel: "статусу",
              valueLabel: this.selectedStatusFilters.join(", "),
            });
          }
          if (this.activeSection === "deals" && this.dealCompanyFilterId) {
            rows.push({
              key: "deal_company",
              fieldLabel: "компании",
              valueLabel: this.resolveSingleFilterLabel(
                this.dealCompanyFilterId,
                this.dealCompanyFilterOptions,
                this.dealCompanyFilterLabel,
                "Компания"
              ),
            });
          }
          if (this.activeSection === "tasks" && this.selectedTaskCompanyFilters.length) {
            rows.push({
              key: "task_company",
              fieldLabel: "компаниям",
              valueLabel: this.resolveMultiFilterLabels(
                this.selectedTaskCompanyFilters,
                this.taskCompanyFilterOptions,
                "Компания"
              ),
            });
          }
          if (this.activeSection === "tasks" && this.selectedTaskCategoryFilters.length) {
            rows.push({
              key: "task_category",
              fieldLabel: "типу",
              valueLabel: this.resolveMultiFilterLabels(
                this.selectedTaskCategoryFilters,
                this.taskCategoryFilterOptions,
                "Категория"
              ),
            });
          }
          if (this.activeSection === "tasks" && this.taskDealFilterId) {
            rows.push({
              key: "task_deal",
              fieldLabel: "сделке",
              valueLabel: this.resolveSingleFilterLabel(
                this.taskDealFilterId,
                this.taskDealFilterOptions,
                this.taskDealFilterLabel,
                "Сделка"
              ),
            });
          }
          if (this.activeSection === "touches" && this.selectedTouchCompanyFilters.length) {
            rows.push({
              key: "touch_company",
              fieldLabel: "компаниям",
              valueLabel: this.resolveMultiFilterLabels(
                this.selectedTouchCompanyFilters,
                this.touchCompanyFilterOptions,
                "Компания"
              ),
            });
          }
          if (this.activeSection === "touches" && this.touchDealFilterId) {
            rows.push({
              key: "touch_deal",
              fieldLabel: "сделке",
              valueLabel: this.resolveSingleFilterLabel(
                this.touchDealFilterId,
                this.touchDealFilterOptions,
                this.touchDealFilterLabel,
                "Сделка"
              ),
            });
          }
          return rows;
        },
        filteredItemsBase() {
          if (this.isTelephonySection || this.isCommunicationsSection) {
            return [];
          }
          const q = this.search.trim().toLowerCase();
          const filtered = this.currentItems.filter((item) => {
            const matchesDealFilter =
              (
                this.activeSection !== "deals" ||
                !this.dealCompanyFilterId ||
                String(item.clientId || "") === String(this.dealCompanyFilterId)
              ) && (
                this.activeSection !== "tasks" ||
                !this.taskDealFilterId ||
                String(item.dealId || "") === String(this.taskDealFilterId)
              ) && (
                this.activeSection !== "touches" ||
                !this.touchDealFilterId ||
                String(item.dealId || "") === String(this.touchDealFilterId)
              );
            const matchesCompanyFilter =
              (
                this.activeSection !== "tasks"
                || !this.selectedTaskCompanyFilters.length
                || this.selectedTaskCompanyFilters.includes(String(item.clientId || ""))
              ) && (
                this.activeSection !== "touches"
                || !this.selectedTouchCompanyFilters.length
                || this.selectedTouchCompanyFilters.includes(String(item.clientId || ""))
              );
            const matchesTaskCategoryFilter =
              this.activeSection !== "tasks"
              || !this.selectedTaskCategoryFilters.length
              || this.selectedTaskCategoryFilters.includes(String(item.taskTypeCategoryId || ""));
            const matchesSearch = !q || [item.name, item.company, item.deal, item.phone, item.email, item.statusLabel]
              .filter(Boolean)
              .some((value) => String(value).toLowerCase().includes(q));
            const matchesStatus =
              !this.selectedStatusFilters.length ||
              this.selectedStatusFilters.includes(item.statusLabel);
            return matchesDealFilter && matchesCompanyFilter && matchesTaskCategoryFilter && matchesSearch && matchesStatus;
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

            if (this.activeSection === "deals") {
              const leftOpenTasks = this.countDealOpenTasks(left.item?.id);
              const rightOpenTasks = this.countDealOpenTasks(right.item?.id);
              if (leftOpenTasks !== rightOpenTasks) {
                return rightOpenTasks - leftOpenTasks;
              }
              const leftCloseTs = this.parseDealCloseDate(left.item?.closeDate)?.getTime() ?? Number.MAX_SAFE_INTEGER;
              const rightCloseTs = this.parseDealCloseDate(right.item?.closeDate)?.getTime() ?? Number.MAX_SAFE_INTEGER;
              if (leftCloseTs !== rightCloseTs) {
                return leftCloseTs - rightCloseTs;
              }
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
        activeStatsQuickFilter() {
          const section = String(this.activeSection || "").trim();
          return String(this.statsQuickFilterBySection?.[section] || "").trim();
        },
        filteredItems() {
          const quickFilter = this.activeStatsQuickFilter;
          if (!quickFilter) {
            return this.filteredItemsBase;
          }
          return this.filteredItemsBase.filter((item) => this.itemMatchesStatsQuickFilter(item, quickFilter));
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
        dealCompanyFilterOptions() {
          if (this.activeSection !== "deals") {
            return [];
          }
          const filteredDeals = (this.datasets.deals || []).filter((deal) => (
            !this.selectedStatusFilters.length
            || this.selectedStatusFilters.includes(deal.statusLabel)
          ));
          const uniqueCompanies = new Map();
          filteredDeals.forEach((deal) => {
            const companyId = String(this.toIntOrNull(deal.clientId));
            if (!companyId || uniqueCompanies.has(companyId)) {
              return;
            }
            uniqueCompanies.set(companyId, {
              value: companyId,
              label: String(deal.company || `Компания #${companyId}`).trim(),
            });
          });
          return Array.from(uniqueCompanies.values()).sort((left, right) => (
            String(left.label).localeCompare(String(right.label), "ru")
          ));
        },
        taskCompanyFilterOptions() {
          if (this.activeSection !== "tasks") {
            return [];
          }
          const activeTasks = (this.datasets.tasks || []).filter((task) => {
            const status = String(task.taskStatus || task.status || "").trim();
            return status !== "done" && status !== "canceled" && this.toIntOrNull(task.clientId);
          });
          const uniqueCompanies = new Map();
          activeTasks.forEach((task) => {
            const companyId = String(this.toIntOrNull(task.clientId));
            if (!companyId || uniqueCompanies.has(companyId)) {
              return;
            }
            uniqueCompanies.set(companyId, {
              value: companyId,
              label: String(task.company || `Компания #${companyId}`).trim(),
            });
          });
          return Array.from(uniqueCompanies.values()).sort((left, right) => (
            String(left.label).localeCompare(String(right.label), "ru")
          ));
        },
        taskCategoryFilterOptions() {
          if (this.activeSection !== "tasks") {
            return [];
          }
          return (Array.isArray(this.metaOptions.taskCategories) ? this.metaOptions.taskCategories : [])
            .filter((category) => this.toIntOrNull(category?.id))
            .map((category) => ({
              value: String(this.toIntOrNull(category.id)),
              label: String(category.name || "").trim(),
              sortOrder: Number(category.sort_order || 0),
            }))
            .filter((category) => category.label)
            .sort((left, right) => {
              if (left.sortOrder !== right.sortOrder) {
                return left.sortOrder - right.sortOrder;
              }
              return String(left.label).localeCompare(String(right.label), "ru");
            })
            .map(({ value, label }) => ({ value, label }));
        },
        taskDealFilterOptions() {
          if (this.activeSection !== "tasks") {
            return [];
          }
          const filteredTasks = (this.datasets.tasks || []).filter((task) => (
            (!this.selectedTaskCompanyFilters.length || this.selectedTaskCompanyFilters.includes(String(task.clientId || "")))
            && (!this.selectedTaskCategoryFilters.length || this.selectedTaskCategoryFilters.includes(String(task.taskTypeCategoryId || "")))
          ));
          const uniqueDeals = new Map();
          filteredTasks.forEach((task) => {
            const dealId = String(this.toIntOrNull(task.dealId));
            if (!dealId || uniqueDeals.has(dealId)) {
              return;
            }
            uniqueDeals.set(dealId, {
              value: dealId,
              label: String(task.deal || `Сделка #${dealId}`).trim(),
            });
          });
          return Array.from(uniqueDeals.values()).sort((left, right) => (
            String(left.label).localeCompare(String(right.label), "ru")
          ));
        },
        touchCompanyFilterOptions() {
          if (this.activeSection !== "touches") {
            return [];
          }
          const uniqueCompanies = new Map();
          (this.datasets.touches || []).forEach((touch) => {
            const companyId = String(this.toIntOrNull(touch.clientId));
            if (!companyId || uniqueCompanies.has(companyId)) {
              return;
            }
            uniqueCompanies.set(companyId, {
              value: companyId,
              label: String(touch.company || `Компания #${companyId}`).trim(),
            });
          });
          return Array.from(uniqueCompanies.values()).sort((left, right) => (
            String(left.label).localeCompare(String(right.label), "ru")
          ));
        },
        touchDealFilterOptions() {
          if (this.activeSection !== "touches") {
            return [];
          }
          const filteredByCompany = (this.datasets.touches || []).filter((touch) => (
            !this.selectedTouchCompanyFilters.length
            || this.selectedTouchCompanyFilters.includes(String(touch.clientId || ""))
          ));
          const uniqueDeals = new Map();
          filteredByCompany.forEach((touch) => {
            const dealId = String(this.toIntOrNull(touch.dealId));
            if (!dealId || uniqueDeals.has(dealId)) {
              return;
            }
            uniqueDeals.set(dealId, {
              value: dealId,
              label: String(touch.deal || `Сделка #${dealId}`).trim(),
            });
          });
          return Array.from(uniqueDeals.values()).sort((left, right) => (
            String(left.label).localeCompare(String(right.label), "ru")
          ));
        },
        stats() {
          const items = this.filteredItemsBase;
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

          const companies = this.filteredItemsBase;
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
        },
        filteredTaskTypeOptions() {
          return this.filterTaskTypesByCategory(this.forms.tasks.taskCategoryId);
        },
        filteredTaskCategoryOptions() {
          return this.filterTaskCategories();
        }
      },
      watch: {
        showModal(nextValue) {
          if (!nextValue) return;
          const target = this.resolveActivePhoneCallHistoryTarget();
          if (!target) return;
          this.ensurePhoneCallHistoryLoaded(target.entityType, target.entityId).catch(() => {});
        },
        activeSection(nextValue, previousValue) {
          this.syncStatusFiltersForSection(previousValue);
          this.syncStatsQuickFilterForSection(previousValue);
          this.applyStatusFiltersForSection(nextValue);
          this.applyStatsQuickFilterForSection(nextValue);
          if (
            this.isSectionLazyLoadingReady
            && nextValue
            && !this.isTelephonySection
            && !this.isCommunicationsSection
            && !this.sectionCollectionState?.[nextValue]?.loaded
            && !this.isLoading
          ) {
            this.reloadActiveSection();
          }
          if (this.isSectionLazyLoadingReady && this.sectionUsesAutomationData(nextValue)) {
            this.ensureAutomationDataLoaded().catch(() => {});
            this.ensureAutomationNotificationsPolling();
          }
        },
        "forms.tasks.taskCategoryId": {
          handler() {
            this.syncTaskCategorySelection(this.forms.tasks);
          }
        },
        "forms.tasks.taskTypeId": {
          handler(nextValue, previousValue) {
            this.syncTaskTypeSelection(this.forms.tasks);
            const nextDefaultResult = this.resolveTaskTypeDefaultResultById(nextValue);
            const previousDefaultResult = this.resolveTaskTypeDefaultResultById(previousValue);
            const currentResult = String(this.forms.tasks.result || "").trim();
            if (!nextDefaultResult) {
              return;
            }
            if (!currentResult || currentResult === previousDefaultResult) {
              this.forms.tasks.result = nextDefaultResult;
            }
          }
        },
        "forms.tasks.dealId": {
          handler() {
            if (this.activeSection === "tasks" && this.showModal) {
              this.loadTaskTouchOptions();
            }
          }
        },
        "forms.tasks.leadId": {
          handler() {
            if (this.activeSection === "tasks" && this.showModal) {
              this.loadTaskTouchOptions();
            }
          }
        },
        "forms.tasks.companyId": {
          handler() {
            const selectedDealId = this.toIntOrNull(this.forms.tasks.dealId);
            if (selectedDealId) {
              const dealStillAvailable = this.filteredTaskDealOptions.some(
                (deal) => String(deal.id) === String(selectedDealId)
              );
              if (!dealStillAvailable) {
                this.forms.tasks.dealId = null;
              }
            }
            if (this.activeSection === "tasks" && this.showModal) {
              this.loadTaskTouchOptions();
            }
          }
        },
        "forms.touches.companyId": {
          handler() {
            const selectedContactId = this.toIntOrNull(this.forms.touches.contactId);
            if (!selectedContactId) {
            } else {
              const contactStillAvailable = this.touchContactOptions.some(
                (contact) => String(contact.id) === String(selectedContactId)
              );
              if (!contactStillAvailable) {
                this.forms.touches.contactId = null;
              }
            }

            const selectedLeadId = this.toIntOrNull(this.forms.touches.leadId);
            if (selectedLeadId) {
              const leadStillAvailable = this.touchLeadOptions.some(
                (lead) => String(lead.id) === String(selectedLeadId)
              );
              if (!leadStillAvailable) {
                this.forms.touches.leadId = null;
              }
            }

            const selectedDealId = this.toIntOrNull(this.forms.touches.dealId);
            if (selectedDealId) {
              const dealStillAvailable = this.touchDealOptions.some(
                (deal) => String(deal.id) === String(selectedDealId)
              );
              if (!dealStillAvailable) {
                this.forms.touches.dealId = null;
              }
            }

            const selectedTaskId = this.toIntOrNull(this.forms.touches.taskId);
            if (selectedTaskId && this.toIntOrNull(this.forms.touches.dealId)) {
              const taskStillAvailable = (this.datasets.tasks || []).some(
                (task) => String(task.id) === String(selectedTaskId)
                  && String(task.dealId || "") === String(this.forms.touches.dealId)
              );
              if (!taskStillAvailable) {
                this.forms.touches.taskId = null;
              }
            }
            if (this.activeSection === "touches" && this.showModal) {
              const companyId = this.toIntOrNull(this.forms.touches.companyId);
              if (!companyId) {
                this.touchCompanyDocuments = [];
                this.forms.touches.clientDocumentIds = [];
                if (this.forms.touches.documentUploadTarget === "company") {
                  this.forms.touches.documentUploadTarget = this.toIntOrNull(this.forms.touches.dealId) ? "deal" : "";
                }
              } else {
                this.loadTouchContactsForSelectedCompany();
              }
              this.loadTouchDocuments();
            }
            this.applyTouchOwnerFromContext();
          }
        },
        showModal(value) {
          if (!value || this.activeSection !== "touches") {
            return;
          }
          this.loadTouchContactsForSelectedCompany();
        },
        "forms.touches.dealId": {
          handler() {
            const selectedTaskId = this.toIntOrNull(this.forms.touches.taskId);
            if (selectedTaskId) {
              const taskStillAvailable = (this.datasets.tasks || []).some(
                (task) => String(task.id) === String(selectedTaskId)
                  && String(task.dealId || "") === String(this.forms.touches.dealId || "")
              );
              if (!taskStillAvailable) {
                this.forms.touches.taskId = null;
              }
            }
            if (this.activeSection === "touches" && this.showModal) {
              const dealId = this.toIntOrNull(this.forms.touches.dealId);
              if (!dealId) {
                this.touchDealDocuments = [];
                this.forms.touches.dealDocumentIds = [];
                if (this.forms.touches.documentUploadTarget === "deal") {
                  this.forms.touches.documentUploadTarget = this.toIntOrNull(this.forms.touches.companyId) ? "company" : "";
                }
              } else if (!this.forms.touches.documentUploadTarget) {
                this.forms.touches.documentUploadTarget = "deal";
              }
              this.loadTouchDocuments();
            }
            this.applyTouchOwnerFromContext();
          }
        },
        "forms.touches.leadId": {
          handler() {
            this.applyTouchOwnerFromContext();
          }
        },
        "forms.touches.taskId": {
          handler() {
            this.applyTouchOwnerFromContext();
          }
        },
        "forms.touches.channelId": {
          handler() {
            const currentResultId = this.toIntOrNull(this.forms.touches.resultOptionId);
            if (currentResultId) {
              const availableIds = this.availableTouchResults(this.forms.touches.channelId, currentResultId).map((item) => String(item.id));
              if (!availableIds.includes(String(currentResultId))) {
                this.forms.touches.resultOptionId = null;
              }
            }
            this.$nextTick(() => this.applyTouchAutomationRule());
          }
        },
        "forms.touches.direction": {
          handler() {
            this.$nextTick(() => this.applyTouchAutomationRule());
          }
        },
        "forms.touches.resultOptionId": {
          handler() {
            if (this.toIntOrNull(this.forms.touches.resultOptionId)) {
              this.setTouchResultPrompt("");
            }
            this.$nextTick(() => this.applyTouchAutomationRule());
          }
        },
        "unboundConversationBindForm.clientId": {
          handler(nextValue) {
            const companyId = this.toIntOrNull(nextValue);
            if (!companyId) {
              this.unboundConversationBindForm.contactId = null;
              this.unboundConversationBindForm.dealId = null;
              return;
            }
            const availableContactIds = this.unboundConversationContactOptions.map((item) => String(item.id));
            const selectedContactId = String(this.toIntOrNull(this.unboundConversationBindForm.contactId) || "");
            if (selectedContactId && !availableContactIds.includes(selectedContactId)) {
              this.unboundConversationBindForm.contactId = null;
            }
            const availableDealIds = this.unboundConversationDealOptions.map((item) => String(item.id));
            const selectedDealId = String(this.toIntOrNull(this.unboundConversationBindForm.dealId) || "");
            if (selectedDealId && !availableDealIds.includes(selectedDealId)) {
              this.unboundConversationBindForm.dealId = null;
            }
          }
        },
        "taskFollowUpForm.taskCategoryId": {
          handler() {
            this.syncTaskCategorySelection(this.taskFollowUpForm);
          }
        },
        "taskFollowUpForm.taskTypeId": {
          handler() {
            this.syncTaskTypeSelection(this.taskFollowUpForm);
          }
        },
        "dealTaskForm.taskCategoryId": {
          handler() {
            this.syncTaskCategorySelection(this.dealTaskForm);
          }
        },
        "dealTaskForm.taskTypeId": {
          handler() {
            this.syncTaskTypeSelection(this.dealTaskForm);
          }
        },
        "touchFollowUpForm.taskCategoryId": {
          handler() {
            this.syncTaskCategorySelection(this.touchFollowUpForm);
          }
        },
        "touchFollowUpForm.taskTypeId": {
          handler() {
            this.syncTaskTypeSelection(this.touchFollowUpForm);
          }
        },
        "forms.deals.description": {
          handler() {
            this.$nextTick(() => this.resizeTextareaById("deal-description-textarea"));
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
        parseFlexibleNumber(value) {
          const normalized = String(value ?? "")
            .replace(/\s+/g, "")
            .replace(",", ".")
            .trim();
          if (!normalized) {
            return 0;
          }
          const numeric = Number(normalized);
          return Number.isFinite(numeric) ? numeric : 0;
        },
        resizeTextareaById(id) {
          const element = document.getElementById(id);
          if (!element) return;
          element.style.height = "0px";
          element.style.height = `${Math.max(element.scrollHeight, 44)}px`;
        },
        scrollPanelIntoView(panelId) {
          const normalizedId = String(panelId || "").trim();
          if (!normalizedId) return;
          this.$nextTick(() => {
            const panel = document.getElementById(normalizedId);
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
        },
        autoResizeTextarea(event) {
          const element = event?.target;
          if (!element) return;
          element.style.height = "0px";
          element.style.height = `${Math.max(element.scrollHeight, 44)}px`;
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
        resolveBankFieldsMode(currency) {
          const normalizedCurrency = String(currency || "").trim().toUpperCase();
          if (normalizedCurrency === "RUB") return "ru";
          if (normalizedCurrency === "KZT") return "kz";
          return "intl";
        },
        companyUsesRussianBankFields(currency) {
          return this.resolveBankFieldsMode(currency) === "ru";
        },
        companyTypeLabel(value) {
          const normalized = String(value || "client").trim() || "client";
          return (this.companyTypeOptions || []).find((item) => String(item.value || "") === normalized)?.label || "Клиент";
        },
        companyPrimaryBankAccountLabel(currency) {
          const mode = this.resolveBankFieldsMode(currency);
          if (mode === "ru") return "Расчетный счет";
          if (mode === "kz") return "ИИК / IBAN";
          return "IBAN";
        },
        companyBankCodeLabel(currency) {
          return this.resolveBankFieldsMode(currency) === "intl" ? "SWIFT / BIC" : "БИК";
        },
        novofonCallTargetKey(entityType, entityId, phone) {
          const normalizedEntityType = String(entityType || "").trim();
          const normalizedEntityId = this.toIntOrNull(entityId);
          const normalizedPhone = String(phone || "").trim();
          return [normalizedEntityType, normalizedEntityId || "", normalizedPhone].join(":");
        },
        isNovofonCallStartingFor(entityType, entityId, phone) {
          return this.isNovofonCallStarting
            && this.activeNovofonCallTarget === this.novofonCallTargetKey(entityType, entityId, phone);
        },
        async startNovofonCall({ phone = "", entityType = "", entityId = null, comment = "" } = {}) {
          const normalizedPhone = String(phone || "").trim();
          const normalizedEntityType = String(entityType || "").trim();
          const normalizedEntityId = this.toIntOrNull(entityId);
          if (!normalizedPhone || !normalizedEntityType || !normalizedEntityId) {
            this.setUiError("Недостаточно данных для запуска звонка.", { modal: true });
            return;
          }
          const targetKey = this.novofonCallTargetKey(normalizedEntityType, normalizedEntityId, normalizedPhone);
          if (this.isNovofonCallStarting && this.activeNovofonCallTarget === targetKey) {
            return;
          }
          this.clearUiErrors({ modalOnly: true });
          this.isNovofonCallStarting = true;
          this.activeNovofonCallTarget = targetKey;
          try {
            await this.apiRequest("/api/telephony/novofon/call/", {
              method: "POST",
              body: {
                phone: normalizedPhone,
                entity_type: normalizedEntityType,
                entity_id: normalizedEntityId,
                comment: String(comment || "").trim(),
              }
            });
            this.refreshPhoneCallHistory(normalizedEntityType, normalizedEntityId).catch(() => {});
          } catch (error) {
            this.setUiError(`Ошибка запуска звонка: ${error.message}`, { modal: true });
          } finally {
            this.isNovofonCallStarting = false;
            this.activeNovofonCallTarget = "";
          }
        },
        emailHref(value) {
          const normalized = String(value || "").trim();
          return normalized ? `mailto:${normalized}` : "";
        },
        normalizePaginatedResponse(data) {
          if (Array.isArray(data)) return data;
          if (data && Array.isArray(data.results)) return data.results;
          return [];
        },
        clearTelephonyNotice() {
          this.telephonyNotice = { type: "", text: "" };
        },
        setTelephonyNotice(text, type = "success") {
          this.telephonyNotice = {
            type: String(type || "success").trim() || "success",
            text: String(text || "").trim(),
          };
        },
        normalizeTelephonyHealth(payload = {}) {
          const counts = (payload.counts && typeof payload.counts === "object" && !Array.isArray(payload.counts))
            ? payload.counts
            : {};
          const problemEvents = Array.isArray(payload.problem_events)
            ? payload.problem_events.map((item) => ({
              id: this.toIntOrNull(item.id),
              eventType: String(item.event_type || "").trim(),
              externalCallId: String(item.external_call_id || "").trim(),
              externalEventId: String(item.external_event_id || "").trim(),
              status: String(item.status || "").trim(),
              errorText: String(item.error_text || "").trim(),
              receivedAt: String(item.received_at || "").trim(),
              processedAt: String(item.processed_at || "").trim(),
              retryCount: Math.max(0, Number(item.retry_count) || 0),
              isStaleProcessing: !!item.is_stale_processing,
            }))
            : [];
          return {
            counts: {
              queued: Math.max(0, Number(counts.queued) || 0),
              failed: Math.max(0, Number(counts.failed) || 0),
              processing: Math.max(0, Number(counts.processing) || 0),
              staleProcessing: Math.max(0, Number(counts.stale_processing) || 0),
              processed: Math.max(0, Number(counts.processed) || 0),
              ignoredDuplicate: Math.max(0, Number(counts.ignored_duplicate) || 0),
            },
            latestEventAt: String(payload.latest_event_at || "").trim(),
            oldestQueuedAt: String(payload.oldest_queued_at || "").trim(),
            staleProcessingAfterSeconds: Math.max(0, Number(payload.stale_processing_after_seconds) || 0),
            problemEvents,
          };
        },
        telephonyHealthEventStatusLabel(event = {}) {
          const status = String(event.status || "").trim().toLowerCase();
          if (status === "failed") return "Ошибка";
          if (status === "queued") return "В очереди";
          if (status === "processing") return event.isStaleProcessing ? "Зависло в processing" : "Обрабатывается";
          if (status === "processed") return "Обработано";
          if (status === "ignored_duplicate") return "Дубликат";
          return status || "Неизвестно";
        },
        telephonyHealthEventStatusClass(event = {}) {
          const status = String(event.status || "").trim().toLowerCase();
          if (status === "failed") return "border-red-400/30 bg-red-400/10 text-red-200";
          if (status === "queued") return "border-amber-400/30 bg-amber-400/10 text-amber-200";
          if (status === "processing" && event.isStaleProcessing) return "border-orange-400/30 bg-orange-400/10 text-orange-200";
          if (status === "processing") return "border-sky-400/30 bg-sky-400/10 text-sky-200";
          return "border-crm-border bg-[#12324e] text-crm-text";
        },
        async loadTelephonyHealth() {
          this.isTelephonyHealthLoading = true;
          try {
            const payload = await this.apiRequest("/api/admin/telephony/health/");
            this.telephonyHealth = this.normalizeTelephonyHealth(payload);
          } catch (error) {
            this.setTelephonyNotice(`Ошибка загрузки health-среза: ${error.message}`, "error");
          } finally {
            this.isTelephonyHealthLoading = false;
          }
        },
        async reprocessTelephonyEvent(eventId) {
          const normalizedEventId = this.toIntOrNull(eventId);
          if (!normalizedEventId) return;
          try {
            await this.apiRequest(`/api/admin/telephony/events/${normalizedEventId}/reprocess/`, {
              method: "POST",
            });
            this.setTelephonyNotice(`Событие #${normalizedEventId} возвращено в очередь.`);
            await this.loadTelephonyHealth();
          } catch (error) {
            this.setTelephonyNotice(`Ошибка reprocess события #${normalizedEventId}: ${error.message}`, "error");
          }
        },
        incomingCallPopupStorageKey() {
          return `crm_seen_incoming_calls_v1_${String(this.currentUserId || "anon")}`;
        },
        incomingCallPopupKey(call = {}) {
          return String(call.external_call_id || call.id || "").trim();
        },
        readSeenIncomingCallPopupMap() {
          if (typeof window === "undefined") return {};
          try {
            const raw = window.localStorage.getItem(this.incomingCallPopupStorageKey());
            const parsed = raw ? JSON.parse(raw) : {};
            const cutoff = Date.now() - (6 * 60 * 60 * 1000);
            const normalized = {};
            Object.entries(parsed || {}).forEach(([key, value]) => {
              const numericValue = Number(value) || 0;
              if (key && numericValue >= cutoff) {
                normalized[key] = numericValue;
              }
            });
            window.localStorage.setItem(this.incomingCallPopupStorageKey(), JSON.stringify(normalized));
            return normalized;
          } catch (_) {
            return {};
          }
        },
        markIncomingCallPopupSeen(call = {}) {
          const popupKey = this.incomingCallPopupKey(call);
          if (!popupKey || typeof window === "undefined") return;
          const seenMap = this.readSeenIncomingCallPopupMap();
          seenMap[popupKey] = Date.now();
          try {
            window.localStorage.setItem(this.incomingCallPopupStorageKey(), JSON.stringify(seenMap));
          } catch (_) {}
        },
        hasSeenIncomingCallPopup(call = {}) {
          const popupKey = this.incomingCallPopupKey(call);
          if (!popupKey) return false;
          const seenMap = this.readSeenIncomingCallPopupMap();
          return !!seenMap[popupKey];
        },
        enqueueIncomingCallPopup(call = {}) {
          const popupKey = this.incomingCallPopupKey(call);
          if (!popupKey || this.hasSeenIncomingCallPopup(call)) {
            return;
          }
          const alreadyVisible = (this.telephonyIncomingCallPopups || []).some((item) => this.incomingCallPopupKey(item) === popupKey);
          if (alreadyVisible) {
            return;
          }
          this.markIncomingCallPopupSeen(call);
          this.telephonyIncomingCallPopups = [
            {
              ...call,
              popupKey,
            },
            ...(this.telephonyIncomingCallPopups || []),
          ].slice(0, 3);
        },
        dismissIncomingCallPopup(callOrKey) {
          const popupKey = typeof callOrKey === "string"
            ? String(callOrKey || "").trim()
            : this.incomingCallPopupKey(callOrKey || {});
          if (!popupKey) return;
          this.telephonyIncomingCallPopups = (this.telephonyIncomingCallPopups || []).filter(
            (item) => this.incomingCallPopupKey(item) !== popupKey
          );
        },
        incomingCallPopupStatusLabel(call = {}) {
          const statusLabel = this.phoneCallStatusLabel(call.status);
          if (statusLabel && statusLabel !== "Неизвестно") {
            return statusLabel;
          }
          return "Входящий";
        },
        incomingCallPopupTargetTypeLabel(call = {}) {
          const targetEntityType = String(call.target_entity_type || "").trim();
          if (targetEntityType === "deal") return "Сделка";
          if (targetEntityType === "lead") return "Лид";
          if (targetEntityType === "contact") return "Контакт";
          if (targetEntityType === "company") return "Компания";
          return "";
        },
        incomingCallPopupOpenTarget(call = {}) {
          const targetEntityType = String(call.target_entity_type || "").trim();
          const targetEntityId = this.toIntOrNull(call.target_entity_id);
          this.dismissIncomingCallPopup(call);
          if (!targetEntityType || !targetEntityId) {
            return;
          }
          if (targetEntityType === "deal") {
            this.setSection("deals");
            this.openDealEditorById(targetEntityId);
            return;
          }
          if (targetEntityType === "lead") {
            this.setSection("leads");
            this.openLeadEditorById(targetEntityId);
            return;
          }
          if (targetEntityType === "contact") {
            this.setSection("contacts");
            this.openContactEditorById(targetEntityId);
            return;
          }
          if (targetEntityType === "company") {
            this.setSection("companies");
            this.openCompanyEditorById(targetEntityId);
          }
        },
        ensureTelephonyIncomingCallsPolling() {
          if (this.telephonyIncomingCallsPollTimer || typeof window === "undefined") return;
          this.pollTelephonyIncomingCalls().catch(() => {});
          this.telephonyIncomingCallsPollTimer = window.setInterval(() => {
            this.pollTelephonyIncomingCalls().catch(() => {});
          }, 5000);
        },
        stopTelephonyIncomingCallsPolling() {
          if (this.telephonyIncomingCallsPollTimer && typeof window !== "undefined") {
            window.clearInterval(this.telephonyIncomingCallsPollTimer);
          }
          this.telephonyIncomingCallsPollTimer = null;
          this.isTelephonyIncomingCallsPolling = false;
        },
        async pollTelephonyIncomingCalls() {
          if (this.isTelephonyIncomingCallsPolling) return;
          if (typeof document !== "undefined" && document.hidden) return;
          this.isTelephonyIncomingCallsPolling = true;
          try {
            const params = new URLSearchParams();
            if (this.toIntOrNull(this.telephonyIncomingCallCursor)) {
              params.set("after_id", String(this.toIntOrNull(this.telephonyIncomingCallCursor)));
            }
            params.set("limit", "20");
            const query = params.toString();
            const payload = await this.apiRequest(`/api/telephony/incoming-calls/popup/${query ? `?${query}` : ""}`);
            const items = Array.isArray(payload?.items) ? payload.items : [];
            const nextCallId = this.toIntOrNull(payload?.next_call_id);
            if (nextCallId) {
              this.telephonyIncomingCallCursor = nextCallId;
            }
            items.forEach((item) => this.enqueueIncomingCallPopup(item));
            if (payload?.has_more) {
              window.setTimeout(() => {
                this.pollTelephonyIncomingCalls().catch(() => {});
              }, 200);
            }
          } catch (_) {
          } finally {
            this.isTelephonyIncomingCallsPolling = false;
          }
        },
        normalizeTelephonySettings(payload = {}) {
          const allowedVirtualNumbersText = Array.isArray(payload.allowed_virtual_numbers)
            ? payload.allowed_virtual_numbers.map((item) => String(item || "").trim()).filter(Boolean).join("\n")
            : "";
          const mappings = Array.isArray(payload.mappings)
            ? payload.mappings.map((item) => ({
              id: this.toIntOrNull(item.id),
              crmUserId: this.toIntOrNull(item.crm_user),
              crmUserName: String(item.crm_user_name || "").trim(),
              novofonEmployeeId: String(item.novofon_employee_id || "").trim(),
              novofonExtension: String(item.novofon_extension || "").trim(),
              novofonFullName: String(item.novofon_full_name || "").trim(),
              isActive: item.is_active !== false,
              isDefaultOwner: !!item.is_default_owner,
            }))
            : [];
          return {
            enabled: !!payload.enabled,
            apiBaseUrl: String(payload.api_base_url || "").trim(),
            webhookPath: String(payload.webhook_path || "").trim(),
            webhookUrl: String(payload.webhook_url || "").trim(),
            defaultOwnerId: this.toIntOrNull(payload.default_owner),
            createLeadForUnknownNumber: !!payload.create_lead_for_unknown_number,
            createTaskForMissedCall: !!payload.create_task_for_missed_call,
            linkCallsToOpenDealOnly: payload.link_calls_to_open_deal_only !== false,
            allowedVirtualNumbersText,
            isDebugLoggingEnabled: !!payload.is_debug_logging_enabled,
            hasApiSecret: !!payload.has_api_secret,
            lastConnectionCheckedAt: String(payload.last_connection_checked_at || "").trim(),
            lastConnectionStatus: String(payload.last_connection_status || "").trim(),
            lastConnectionError: String(payload.last_connection_error || "").trim(),
            mappings,
            settingsJson: (payload.settings_json && typeof payload.settings_json === "object" && !Array.isArray(payload.settings_json))
              ? { ...payload.settings_json }
              : {},
          };
        },
        telephonyAllowedVirtualNumbersList() {
          return String(this.telephonySettings.allowedVirtualNumbersText || "")
            .split(/\n|,|;/)
            .map((item) => String(item || "").trim())
            .filter(Boolean);
        },
        telephonySettingsSavePayload() {
          return {
            enabled: !!this.telephonySettings.enabled,
            api_base_url: String(this.telephonySettings.apiBaseUrl || "").trim(),
            webhook_path: String(this.telephonySettings.webhookPath || "").trim(),
            default_owner: this.toIntOrNull(this.telephonySettings.defaultOwnerId),
            create_lead_for_unknown_number: !!this.telephonySettings.createLeadForUnknownNumber,
            create_task_for_missed_call: !!this.telephonySettings.createTaskForMissedCall,
            link_calls_to_open_deal_only: !!this.telephonySettings.linkCallsToOpenDealOnly,
            allowed_virtual_numbers: this.telephonyAllowedVirtualNumbersList(),
            is_debug_logging_enabled: !!this.telephonySettings.isDebugLoggingEnabled,
            settings_json: (this.telephonySettings.settingsJson && typeof this.telephonySettings.settingsJson === "object" && !Array.isArray(this.telephonySettings.settingsJson))
              ? { ...this.telephonySettings.settingsJson }
              : {},
            mappings: (this.telephonySettings.mappings || [])
              .filter((item) => String(item.novofonEmployeeId || "").trim())
              .map((item) => ({
                ...(this.toIntOrNull(item.id) ? { id: this.toIntOrNull(item.id) } : {}),
                crm_user: this.toIntOrNull(item.crmUserId),
                novofon_employee_id: String(item.novofonEmployeeId || "").trim(),
                novofon_extension: String(item.novofonExtension || "").trim(),
                novofon_full_name: String(item.novofonFullName || "").trim(),
                is_active: item.isActive !== false,
                is_default_owner: !!item.isDefaultOwner,
              })),
          };
        },
        async loadTelephonySettings(force = false) {
          if (this.telephonySettingsLoaded && !force) {
            return;
          }
          this.isTelephonySettingsLoading = true;
          this.errorMessage = "";
          try {
            const payload = await this.apiRequest("/api/telephony/novofon/settings/");
            this.telephonySettings = this.normalizeTelephonySettings(payload);
            this.telephonySettingsLoaded = true;
            await this.loadTelephonyHealth();
          } catch (error) {
            this.errorMessage = `Ошибка загрузки телефонии: ${error.message}`;
            throw error;
          } finally {
            this.isTelephonySettingsLoading = false;
          }
        },
        async saveTelephonySettings() {
          this.isTelephonySettingsSaving = true;
          this.clearTelephonyNotice();
          this.errorMessage = "";
          try {
            const payload = await this.apiRequest("/api/telephony/novofon/settings/", {
              method: "PUT",
              body: this.telephonySettingsSavePayload(),
            });
            this.telephonySettings = this.normalizeTelephonySettings(payload);
            this.telephonySettingsLoaded = true;
            await this.loadTelephonyHealth();
            this.setTelephonyNotice("Настройки телефонии сохранены.");
          } catch (error) {
            this.setTelephonyNotice(`Ошибка сохранения: ${error.message}`, "error");
          } finally {
            this.isTelephonySettingsSaving = false;
          }
        },
        async checkTelephonyConnection() {
          this.isTelephonyConnectionChecking = true;
          this.clearTelephonyNotice();
          this.errorMessage = "";
          try {
            const result = await this.apiRequest("/api/telephony/novofon/check-connection/", {
              method: "POST",
            });
            await this.loadTelephonySettings(true);
            if (result && result.ok) {
              const virtualNumbersCount = Number(result?.payload?.virtual_numbers_count || 0);
              this.setTelephonyNotice(`Подключение проверено. Активных виртуальных номеров: ${virtualNumbersCount}.`);
            } else {
              this.setTelephonyNotice(`Проверка завершилась ошибкой: ${result?.error || "неизвестная ошибка"}`, "error");
            }
          } catch (error) {
            this.setTelephonyNotice(`Ошибка проверки подключения: ${error.message}`, "error");
          } finally {
            this.isTelephonyConnectionChecking = false;
          }
        },
        async syncTelephonyEmployees() {
          this.isTelephonyEmployeesSyncing = true;
          this.clearTelephonyNotice();
          this.errorMessage = "";
          try {
            const payload = await this.apiRequest("/api/telephony/novofon/sync-employees/", {
              method: "POST",
            });
            this.telephonySettings = this.normalizeTelephonySettings(payload);
            this.telephonySettingsLoaded = true;
            await this.loadTelephonyHealth();
            const syncedCount = Number(payload?.sync_result?.count || 0);
            this.setTelephonyNotice(`Синхронизация завершена. Обновлено сотрудников: ${syncedCount}.`);
          } catch (error) {
            this.setTelephonyNotice(`Ошибка синхронизации сотрудников: ${error.message}`, "error");
          } finally {
            this.isTelephonyEmployeesSyncing = false;
          }
        },
        async importTelephonyCalls() {
          this.isTelephonyCallsImporting = true;
          this.clearTelephonyNotice();
          this.errorMessage = "";
          this.telephonyLastImportResult = null;
          try {
            const result = await this.apiRequest("/api/telephony/novofon/import-calls/", {
              method: "POST",
              body: {
                days: Math.max(1, Number(this.telephonyImportForm.days || 30)),
                limit: Math.max(1, Number(this.telephonyImportForm.limit || 500)),
                max_records: Math.max(1, Number(this.telephonyImportForm.maxRecords || 5000)),
                include_ongoing_calls: !!this.telephonyImportForm.includeOngoingCalls,
              },
            });
            this.telephonyLastImportResult = result;
            await this.loadTelephonyHealth();
            this.setTelephonyNotice(
              `Импорт завершён. Создано: ${Number(result?.created || 0)}, обновлено: ${Number(result?.updated || 0)}, всего обработано: ${Number(result?.imported || 0)}.`
            );
          } catch (error) {
            this.setTelephonyNotice(`Ошибка импорта звонков: ${error.message}`, "error");
          } finally {
            this.isTelephonyCallsImporting = false;
          }
        },
        resolveActivePhoneCallHistoryTarget() {
          if (this.activeSection === "leads" && this.toIntOrNull(this.editingLeadId)) {
            return { entityType: "lead", entityId: this.toIntOrNull(this.editingLeadId) };
          }
          if (this.activeSection === "deals" && this.toIntOrNull(this.editingDealId)) {
            return { entityType: "deal", entityId: this.toIntOrNull(this.editingDealId) };
          }
          if (this.activeSection === "contacts" && this.toIntOrNull(this.editingContactId)) {
            return { entityType: "contact", entityId: this.toIntOrNull(this.editingContactId) };
          }
          if (this.activeSection === "companies" && this.toIntOrNull(this.editingCompanyId)) {
            return { entityType: "company", entityId: this.toIntOrNull(this.editingCompanyId) };
          }
          return null;
        },
        phoneCallHistoryEntityKey(entityType, entityId) {
          const normalizedEntityType = String(entityType || "").trim();
          const normalizedEntityId = this.toIntOrNull(entityId);
          if (!normalizedEntityType || !normalizedEntityId) return "";
          return `${normalizedEntityType}:${normalizedEntityId}`;
        },
        defaultPhoneCallHistoryState() {
          return {
            loading: false,
            error: "",
            items: [],
            count: 0,
            next: "",
            previous: "",
            page: 1,
            currentFilter: "all",
            cache: {},
          };
        },
        getPhoneCallHistoryEntityState(entityType, entityId, createIfMissing = true) {
          const entityKey = this.phoneCallHistoryEntityKey(entityType, entityId);
          if (!entityKey) {
            return this.defaultPhoneCallHistoryState();
          }
          if (!this.phoneCallHistories[entityKey] && createIfMissing) {
            this.phoneCallHistories[entityKey] = this.defaultPhoneCallHistoryState();
          }
          return this.phoneCallHistories[entityKey] || this.defaultPhoneCallHistoryState();
        },
        phoneCallHistoryCacheKey(filterValue, page) {
          return `${String(filterValue || "all").trim() || "all"}:${Math.max(1, Number(page) || 1)}`;
        },
        buildPhoneCallHistoryQuery(entityType, entityId, filterValue, page) {
          const normalizedEntityType = String(entityType || "").trim();
          const normalizedEntityId = this.toIntOrNull(entityId);
          const normalizedFilter = String(filterValue || "all").trim() || "all";
          const normalizedPage = Math.max(1, Number(page) || 1);
          const params = new URLSearchParams({
            entity_type: normalizedEntityType,
            entity_id: String(normalizedEntityId || ""),
            page_size: "10",
            page: String(normalizedPage),
          });
          if (normalizedFilter === "inbound" || normalizedFilter === "outbound") {
            params.set("direction", normalizedFilter);
          } else if (normalizedFilter === "missed") {
            params.set("status", "missed");
          }
          return params.toString();
        },
        applyPhoneCallHistoryState(state, payload, options = {}) {
          const normalizedFilter = String(options.filterValue || state.currentFilter || "all").trim() || "all";
          const normalizedPage = Math.max(1, Number(options.page || payload.page || 1) || 1);
          state.currentFilter = normalizedFilter;
          state.page = normalizedPage;
          state.items = Array.isArray(payload.items) ? payload.items : [];
          state.count = Math.max(0, Number(payload.count) || 0);
          state.next = payload.next || "";
          state.previous = payload.previous || "";
        },
        async loadPhoneCallHistory(entityType, entityId, options = {}) {
          const normalizedEntityType = String(entityType || "").trim();
          const normalizedEntityId = this.toIntOrNull(entityId);
          if (!normalizedEntityType || !normalizedEntityId) {
            return;
          }
          const state = this.getPhoneCallHistoryEntityState(normalizedEntityType, normalizedEntityId, true);
          const filterValue = String(options.filterValue || state.currentFilter || "all").trim() || "all";
          const page = Math.max(1, Number(options.page || state.page || 1) || 1);
          const cacheKey = this.phoneCallHistoryCacheKey(filterValue, page);
          if (!options.force && state.cache[cacheKey]) {
            this.applyPhoneCallHistoryState(state, state.cache[cacheKey], { filterValue, page });
            return;
          }
          state.loading = true;
          state.error = "";
          try {
            const query = this.buildPhoneCallHistoryQuery(normalizedEntityType, normalizedEntityId, filterValue, page);
            const response = await this.apiRequest(`/api/telephony/calls/?${query}`);
            const items = this.normalizePaginatedResponse(response);
            const payload = {
              items,
              count: Number(response?.count) || items.length,
              next: response?.next || "",
              previous: response?.previous || "",
              page,
            };
            state.cache = {
              ...state.cache,
              [cacheKey]: payload,
            };
            this.applyPhoneCallHistoryState(state, payload, { filterValue, page });
          } catch (error) {
            state.error = error.message || "Не удалось загрузить историю звонков.";
          } finally {
            state.loading = false;
          }
        },
        async ensurePhoneCallHistoryLoaded(entityType, entityId) {
          return this.loadPhoneCallHistory(entityType, entityId, { page: 1 });
        },
        async refreshPhoneCallHistory(entityType, entityId) {
          const state = this.getPhoneCallHistoryEntityState(entityType, entityId, true);
          const filterValue = String(state.currentFilter || "all").trim() || "all";
          state.page = 1;
          return this.loadPhoneCallHistory(entityType, entityId, {
            force: true,
            filterValue,
            page: 1,
          });
        },
        async setPhoneCallHistoryFilter(entityType, entityId, filterValue) {
          const state = this.getPhoneCallHistoryEntityState(entityType, entityId, true);
          state.currentFilter = String(filterValue || "all").trim() || "all";
          state.page = 1;
          return this.loadPhoneCallHistory(entityType, entityId, {
            filterValue: state.currentFilter,
            page: 1,
          });
        },
        async goToPhoneCallHistoryPage(entityType, entityId, direction) {
          const state = this.getPhoneCallHistoryEntityState(entityType, entityId, false);
          if (!state) return;
          const step = String(direction || "").trim() === "previous" ? -1 : 1;
          const targetPage = Math.max(1, Number(state.page || 1) + step);
          if (step < 0 && !state.previous) return;
          if (step > 0 && !state.next) return;
          return this.loadPhoneCallHistory(entityType, entityId, {
            filterValue: state.currentFilter || "all",
            page: targetPage,
          });
        },
        phoneCallFilterButtonClass(entityType, entityId, filterValue) {
          const state = this.getPhoneCallHistoryEntityState(entityType, entityId, false);
          const isActive = String(state?.currentFilter || "all") === String(filterValue || "all");
          return isActive
            ? "border-crm-accent bg-crm-accent/15 text-white"
            : "border-crm-border bg-[#123753] text-crm-muted hover:border-crm-accent/70 hover:text-white";
        },
        timelineFilterButtonClass(section, filterValue) {
          const normalizedSection = String(section || "").trim();
          const normalizedValue = String(filterValue || "").trim();
          const selected = Array.isArray(this.timelineFilters?.[normalizedSection]) ? this.timelineFilters[normalizedSection] : [];
          const isActive = selected.includes(normalizedValue);
          return isActive
            ? "border-crm-accent bg-crm-accent/15 text-white"
            : "border-crm-border bg-[#123753] text-crm-muted hover:border-crm-accent/70 hover:text-white";
        },
        toggleTimelineFilter(section, filterValue) {
          const normalizedSection = String(section || "").trim();
          const normalizedValue = String(filterValue || "").trim();
          if (!normalizedSection || !normalizedValue) return;
          const current = Array.isArray(this.timelineFilters?.[normalizedSection]) ? this.timelineFilters[normalizedSection] : [];
          const next = current.includes(normalizedValue)
            ? current.filter((item) => item !== normalizedValue)
            : [...current, normalizedValue];
          this.timelineFilters = {
            ...this.timelineFilters,
            [normalizedSection]: next,
          };
        },
        resolveTimelineEventCategory(eventItem) {
          if (!eventItem || typeof eventItem !== "object") return "";
          const eventType = String(eventItem.eventType || "").trim().toLowerCase();
          const renderType = String(eventItem.renderType || "").trim().toLowerCase();
          const communicationChannel = String(eventItem.communicationChannel || "").trim().toLowerCase();
          const hasCommunicationBinding = !!(
            this.toIntOrNull(eventItem.communicationMessageId)
            || this.toIntOrNull(eventItem.conversationId)
            || communicationChannel
          );
          if (
            renderType === "task"
            || eventType === "task"
            || eventType === "internal_task_completed"
            || eventType.indexOf("client_task_completed_") === 0
          ) {
            return "tasks";
          }
          if (eventType === "touch" || this.toIntOrNull(eventItem.touchId)) {
            if (communicationChannel === "email") {
              return "email";
            }
            if (hasCommunicationBinding) {
              return "messages";
            }
            return "touches";
          }
          return "";
        },
        shouldIncludeTimelineEvent(section, eventItem) {
          const normalizedSection = String(section || "").trim();
          const selected = Array.isArray(this.timelineFilters?.[normalizedSection]) ? this.timelineFilters[normalizedSection] : [];
          const category = this.resolveTimelineEventCategory(eventItem);
          if (!category) {
            return selected.length === this.timelineFilterOptions.length;
          }
          return selected.includes(category);
        },
        filterTimelineItems(section, items) {
          return (Array.isArray(items) ? items : []).filter((eventItem) => this.shouldIncludeTimelineEvent(section, eventItem));
        },
        phoneCallDirectionLabel(direction) {
          const normalized = String(direction || "").trim();
          if (normalized === "inbound") return "Входящий";
          if (normalized === "outbound") return "Исходящий";
          return "Звонок";
        },
        phoneCallStatusLabel(status) {
          const normalized = String(status || "").trim();
          if (normalized === "ringing") return "Звонит";
          if (normalized === "answered") return "Ответили";
          if (normalized === "missed") return "Пропущен";
          if (normalized === "completed") return "Завершен";
          if (normalized === "failed") return "Ошибка";
          if (normalized === "canceled") return "Отменен";
          return normalized || "Неизвестно";
        },
        phoneCallStatusClass(status) {
          const normalized = String(status || "").trim();
          if (normalized === "answered" || normalized === "completed") {
            return "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";
          }
          if (normalized === "missed" || normalized === "failed" || normalized === "canceled") {
            return "border-red-400/30 bg-red-400/10 text-red-300";
          }
          if (normalized === "ringing") {
            return "border-amber-400/30 bg-amber-400/10 text-amber-200";
          }
          return "border-crm-border bg-[#123753] text-white";
        },
        formatCallDuration(totalSeconds) {
          const normalizedSeconds = Math.max(0, Number(totalSeconds) || 0);
          const hours = Math.floor(normalizedSeconds / 3600);
          const minutes = Math.floor((normalizedSeconds % 3600) / 60);
          const seconds = normalizedSeconds % 60;
          if (hours > 0) {
            return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
          }
          return `${minutes}:${String(seconds).padStart(2, "0")}`;
        },
        phoneCallDurationLabel(call) {
          const totalSeconds = Math.max(
            Number(call?.talk_duration_sec) || 0,
            Number(call?.duration_sec) || 0
          );
          if (totalSeconds > 0) {
            return this.formatCallDuration(totalSeconds);
          }
          const status = String(call?.status || "").trim();
          if (status === "missed") return "Без ответа";
          if (status === "ringing") return "Идет вызов";
          if (status === "failed") return "Не состоялся";
          if (status === "canceled") return "Отменен";
          return "—";
        },
        phoneCallDisplayPhone(call) {
          const direction = String(call?.direction || "").trim();
          if (direction === "inbound") {
            return String(call?.phone_from || call?.client_phone_normalized || call?.phone_to || "").trim();
          }
          return String(call?.phone_to || call?.client_phone_normalized || call?.phone_from || "").trim();
        },
        phoneCallStartedLabel(call) {
          return this.formatEventTimestamp(
            call?.started_at
            || call?.answered_at
            || call?.ended_at
            || call?.created_at
            || ""
          );
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
        isOptionalFieldExpanded(section, fieldKey) {
          return !!this.expandedOptionalFields?.[section]?.[fieldKey];
        },
        toggleOptionalField(section, fieldKey) {
          if (!this.expandedOptionalFields[section]) {
            this.expandedOptionalFields[section] = {};
          }
          this.expandedOptionalFields[section] = {
            ...this.expandedOptionalFields[section],
            [fieldKey]: !this.isOptionalFieldExpanded(section, fieldKey),
          };
        },
        resetExpandedOptionalFields() {
          this.expandedOptionalFields = {
            leads: {},
            deals: {},
            companies: {},
            tasks: {}
          };
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
                touchId: null,
                dealId: null,
                conversationId: null,
                communicationMessageId: null,
                communicationChannel: "",
                eventType: "",
                priority: "",
                title: "",
                actorName: "",
                documentName: "",
                documentUrl: "",
                documentScope: "",
                documents: [],
                channelName: "",
                directionLabel: "",
                touchResult: "",
                summaryText: "",
                nextStep: "",
                nextStepAt: "",
                taskTypeName: "",
                taskStatusLabel: "",
                dueAt: "",
                ownerName: "",
                taskResult: "",
                extra: "",
              };
              const contentLines = eventItem.timestamp ? lines.slice(1) : lines.slice();
              const extraLines = [];
              let pendingDocumentName = "";

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
                if (line.indexOf("touch_id:") === 0) {
                  const parsedTouchId = Number.parseInt(line.replace(/^touch_id:\s*/u, "").trim(), 10);
                  eventItem.touchId = Number.isNaN(parsedTouchId) ? null : parsedTouchId;
                  return;
                }
                if (line.indexOf("deal_id:") === 0) {
                  const parsedDealId = Number.parseInt(line.replace(/^deal_id:\s*/u, "").trim(), 10);
                  eventItem.dealId = Number.isNaN(parsedDealId) ? null : parsedDealId;
                  return;
                }
                if (line.indexOf("conversation_id:") === 0) {
                  const parsedConversationId = Number.parseInt(line.replace(/^conversation_id:\s*/u, "").trim(), 10);
                  eventItem.conversationId = Number.isNaN(parsedConversationId) ? null : parsedConversationId;
                  return;
                }
                if (line.indexOf("communication_message_id:") === 0) {
                  const parsedMessageId = Number.parseInt(line.replace(/^communication_message_id:\s*/u, "").trim(), 10);
                  eventItem.communicationMessageId = Number.isNaN(parsedMessageId) ? null : parsedMessageId;
                  return;
                }
                if (line.indexOf("communication_channel:") === 0) {
                  eventItem.communicationChannel = line.replace(/^communication_channel:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("event_type:") === 0) {
                  eventItem.eventType = line.replace(/^event_type:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("priority:") === 0) {
                  eventItem.priority = line.replace(/^priority:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("title:") === 0) {
                  eventItem.title = line.replace(/^title:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("actor_name:") === 0) {
                  eventItem.actorName = line.replace(/^actor_name:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("document_name:") === 0) {
                  const parsedDocumentName = line.replace(/^document_name:\s*/u, "").trim();
                  eventItem.documentName = eventItem.documentName || parsedDocumentName;
                  pendingDocumentName = parsedDocumentName;
                  return;
                }
                if (line.indexOf("document_url:") === 0) {
                  const parsedDocumentUrl = line.replace(/^document_url:\s*/u, "").trim();
                  eventItem.documentUrl = eventItem.documentUrl || parsedDocumentUrl;
                  if (pendingDocumentName || parsedDocumentUrl) {
                    eventItem.documents.push({
                      name: pendingDocumentName || eventItem.documentName || "Документ",
                      url: parsedDocumentUrl,
                    });
                    pendingDocumentName = "";
                  }
                  return;
                }
                if (line.indexOf("document_scope:") === 0) {
                  eventItem.documentScope = line.replace(/^document_scope:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("channel_name:") === 0) {
                  eventItem.channelName = line.replace(/^channel_name:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("direction_label:") === 0) {
                  eventItem.directionLabel = line.replace(/^direction_label:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("touch_result:") === 0) {
                  eventItem.touchResult = line.replace(/^touch_result:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("summary:") === 0) {
                  eventItem.summaryText = line.replace(/^summary:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("next_step:") === 0) {
                  eventItem.nextStep = line.replace(/^next_step:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("next_step_at:") === 0) {
                  eventItem.nextStepAt = line.replace(/^next_step_at:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("task_type_name:") === 0) {
                  eventItem.taskTypeName = line.replace(/^task_type_name:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("task_status_label:") === 0) {
                  eventItem.taskStatusLabel = line.replace(/^task_status_label:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("due_at:") === 0) {
                  eventItem.dueAt = line.replace(/^due_at:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("owner_name:") === 0) {
                  eventItem.ownerName = line.replace(/^owner_name:\s*/u, "").trim();
                  return;
                }
                if (line.indexOf("task_result:") === 0) {
                  eventItem.taskResult = line.replace(/^task_result:\s*/u, "").trim();
                  return;
                }
                extraLines.push(line);
              });

              if (!eventItem.result && !eventItem.taskId && !eventItem.dealId) {
                return {
                  timestamp: eventItem.timestamp,
                  result: contentLines.join("\n") || chunk,
                  taskId: null,
                  touchId: null,
                  dealId: null,
                  eventType: "",
                  priority: "",
                  title: "",
                  actorName: "",
                  documentName: "",
                  documentUrl: "",
                  documentScope: "",
                  documents: [],
                  channelName: "",
                  directionLabel: "",
                  touchResult: "",
                  summaryText: "",
                  nextStep: "",
                  nextStepAt: "",
                  taskTypeName: "",
                  taskStatusLabel: "",
                  dueAt: "",
                  ownerName: "",
                  taskResult: "",
                  extra: "",
                };
              }

              eventItem.extra = extraLines.join("\n").trim();
              eventItem.renderType = "";
              if (eventItem.touchId) {
                eventItem.renderType = "touch";
              } else if (eventItem.taskId || String(eventItem.eventType || "").trim() === "task" || String(eventItem.eventType || "").trim().indexOf("client_task_completed_") === 0 || String(eventItem.eventType || "").trim() === "internal_task_completed") {
                eventItem.renderType = "task";
              } else if (String(eventItem.eventType || "").trim() === "document" || eventItem.documentUrl || eventItem.documentName) {
                eventItem.renderType = "document";
              } else if (String(eventItem.eventType || "").trim() === "system") {
                eventItem.renderType = "system";
              }
              return eventItem;
            })
            .filter(Boolean);
        },
        leadHistoryEventLabel(item) {
          const eventCode = String((item && item.event) || "").trim();
          if (eventCode === "page_view") return "Просмотр страницы";
          if (eventCode === "chat_opened") return "Открытие чата";
          if (eventCode === "first_message_sent") return "Первое сообщение";
          if (eventCode === "phone_clicked") return "Клик по телефону";
          if (eventCode === "messenger_clicked") return "Клик по мессенджеру";
          if (eventCode === "form_submitted") {
            const formType = String((item && item.form_type) || "").trim();
            return formType ? `Отправка формы ${formType}` : "Отправка формы";
          }
          return eventCode || "Событие сайта";
        },
        buildLeadHistoryEventLog(history) {
          const items = Array.isArray(history) ? [...history].reverse() : [];
          return items
            .filter((item) => item && typeof item === "object" && String(item.timestamp || "").trim())
            .map((item) => [
              String(item.timestamp || "").trim(),
              `Результат: ${this.leadHistoryEventLabel(item)}`,
              "event_type: system",
              "priority: low",
              "title: Системное событие",
            ].join("\n"))
            .join("\n\n");
        },
        leadEventLog(leadForm) {
          const form = leadForm && typeof leadForm === "object" ? leadForm : {};
          const storedEvents = String(form.events || "").trim();
          const historyEvents = this.buildLeadHistoryEventLog(form.history);
          if (storedEvents && historyEvents) {
            return `${storedEvents}\n\n${historyEvents}`;
          }
          return storedEvents || historyEvents;
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
        taskCategoryUsesCommunicationChannel(categoryLike) {
          return !!(categoryLike && categoryLike.uses_communication_channel);
        },
        taskCategoryRequiresFollowUp(categoryLike) {
          return !!(categoryLike && categoryLike.requires_follow_up_task_on_done);
        },
        taskCategorySatisfiesDealNextStepRequirement(categoryLike) {
          return !!(categoryLike && categoryLike.satisfies_deal_next_step_requirement);
        },
        resolveTaskCategoryById(taskCategoryId) {
          const normalizedTaskCategoryId = this.toIntOrNull(taskCategoryId);
          if (!normalizedTaskCategoryId) {
            return null;
          }
          return (this.metaOptions.taskCategories || []).find(
            (entry) => String(entry.id) === String(normalizedTaskCategoryId)
          ) || null;
        },
        resolveTaskTypeCategoryIdById(taskTypeId) {
          const taskType = this.resolveTaskTypeById(taskTypeId);
          return this.toIntOrNull(taskType?.category);
        },
        resolveTaskCategoryFromType(taskTypeId) {
          return this.resolveTaskCategoryById(this.resolveTaskTypeCategoryIdById(taskTypeId));
        },
        taskFormCategory(form) {
          if (!form || typeof form !== "object") return null;
          return this.resolveTaskCategoryById(form.taskCategoryId) || this.resolveTaskCategoryFromType(form.taskTypeId);
        },
        taskFormUsesCommunicationChannel(form) {
          return this.taskCategoryUsesCommunicationChannel(this.taskFormCategory(form));
        },
        taskFormRequiresFollowUp(form) {
          return this.taskCategoryRequiresFollowUp(this.taskFormCategory(form));
        },
        taskFormSatisfiesDealNextStepRequirement(form) {
          return this.taskCategorySatisfiesDealNextStepRequirement(this.taskFormCategory(form));
        },
        taskItemUsesCommunicationChannel(task) {
          if (!task || typeof task !== "object") return false;
          if (typeof task.taskTypeCategoryUsesCommunicationChannel === "boolean") {
            return task.taskTypeCategoryUsesCommunicationChannel;
          }
          return this.taskCategoryUsesCommunicationChannel(this.resolveTaskCategoryById(task.taskTypeCategoryId));
        },
        taskItemSatisfiesDealNextStepRequirement(task) {
          if (!task || typeof task !== "object") return false;
          if (typeof task.taskTypeCategorySatisfiesDealNextStepRequirement === "boolean") {
            return task.taskTypeCategorySatisfiesDealNextStepRequirement;
          }
          return this.taskCategorySatisfiesDealNextStepRequirement(this.resolveTaskCategoryById(task.taskTypeCategoryId));
        },
        findPreferredTaskCategoryId({ usesCommunicationChannel = false, requiresFollowUp = false, satisfiesDealNextStepRequirement = false } = {}) {
          const categories = Array.isArray(this.metaOptions.taskCategories) ? this.metaOptions.taskCategories : [];
          const matched = categories.find((category) => (
            !!category.is_active
            && !!category.uses_communication_channel === !!usesCommunicationChannel
            && !!category.requires_follow_up_task_on_done === !!requiresFollowUp
            && !!category.satisfies_deal_next_step_requirement === !!satisfiesDealNextStepRequirement
          ));
          if (matched) {
            return this.toIntOrNull(matched.id);
          }
          const fallback = categories.find((category) => (
            !!category.is_active
            && !!category.uses_communication_channel === !!usesCommunicationChannel
          ));
          return this.toIntOrNull(fallback?.id);
        },
        filterTaskCategories() {
          return Array.isArray(this.metaOptions.taskCategories) ? this.metaOptions.taskCategories : [];
        },
        filterTaskTypesByCategory(taskCategoryId) {
          const normalizedTaskCategoryId = this.toIntOrNull(taskCategoryId);
          const taskTypes = Array.isArray(this.metaOptions.taskTypes) ? this.metaOptions.taskTypes : [];
          if (!normalizedTaskCategoryId) {
            return [];
          }
          return taskTypes.filter((taskType) => {
            if (String(taskType.category || "") !== String(normalizedTaskCategoryId)) {
              return false;
            }
            return true;
          });
        },
        resolveTaskTypeById(taskTypeId) {
          const normalizedTaskTypeId = this.toIntOrNull(taskTypeId);
          if (!normalizedTaskTypeId) {
            return null;
          }
          return (this.metaOptions.taskTypes || []).find(
            (entry) => String(entry.id) === String(normalizedTaskTypeId)
          ) || null;
        },
        resolveTaskTypeDefaultResultById(taskTypeId) {
          const taskType = this.resolveTaskTypeById(taskTypeId);
          return String(taskType?.touch_result || "").trim();
        },
        syncTaskTypeSelection(form) {
          if (!form || typeof form !== "object") return;
          const taskType = this.resolveTaskTypeById(form.taskTypeId);
          if (!taskType) {
            return;
          }
          const taskCategoryId = this.toIntOrNull(taskType.category);
          if (taskCategoryId && this.toIntOrNull(form.taskCategoryId) !== taskCategoryId) {
            form.taskCategoryId = taskCategoryId;
          }
        },
        syncTaskCategorySelection(form) {
          if (!form || typeof form !== "object") return;
          const category = this.resolveTaskCategoryById(form.taskCategoryId);
          if (!category) {
            form.communicationChannelId = null;
            return;
          }
          if (!this.taskCategoryUsesCommunicationChannel(category)) {
            form.communicationChannelId = null;
          }
          const selectedTaskType = this.resolveTaskTypeById(form.taskTypeId);
          if (
            selectedTaskType
            && this.toIntOrNull(selectedTaskType.category) !== this.toIntOrNull(category.id)
          ) {
            form.taskTypeId = null;
          }
        },
        resolveTaskResultValue(formLike) {
          const form = formLike && typeof formLike === "object" ? formLike : {};
          const explicitResult = String(form.result || "").trim();
          if (explicitResult) {
            return explicitResult;
          }
          return this.resolveTaskTypeDefaultResultById(form.taskTypeId);
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
        dealEventCardClass(eventItem) {
          const priority = String(eventItem?.priority || "").trim();
          if (priority === "high") {
            return "border-emerald-400/30 bg-emerald-400/10";
          }
          if (priority === "medium") {
            return "border-sky-400/30 bg-sky-400/10";
          }
          return "border-crm-border/80 bg-[#0f2f4a]";
        },
        dealEventTypeLabel(eventItem) {
          const eventType = String(eventItem?.renderType || eventItem?.eventType || "").trim();
          if (eventType === "touch") return "Касание";
          if (eventType === "task") return "Задача";
          if (eventType === "document") return "Документ";
          if (eventType === "system") return "Система";
          return "";
        },
        eventShortTimestamp(value) {
          const raw = String(value || "").trim();
          if (!raw) return "";
          if (/^\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}$/.test(raw)) {
            const [, rest] = raw.split(".");
            return `${raw.slice(0, 5)} ${raw.slice(11, 16)}`;
          }
          const parsed = new Date(raw);
          if (Number.isNaN(parsed.getTime())) {
            return raw;
          }
          return parsed.toLocaleString("ru-RU", {
            day: "2-digit",
            month: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          }).replace(",", "");
        },
        dealEventIcon(eventItem) {
          const eventType = String(eventItem?.renderType || eventItem?.eventType || "").trim();
          if (eventType === "task") return "☑";
          if (eventType === "document") return "▣";
          if (eventType === "system") return "•";
          const channel = String(eventItem?.channelName || eventItem?.title || "").toLowerCase();
          if (channel.includes("звон")) return "☎";
          if (channel.includes("email") || channel.includes("почт")) return "✉";
          if (channel.includes("встреч")) return "◈";
          if (channel.includes("док")) return "▣";
          return "◉";
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
        async fetchLeadById(leadId) {
          const normalizedLeadId = this.toIntOrNull(leadId);
          if (!normalizedLeadId) {
            throw new Error("Некорректный ID лида");
          }

          const existingLead = this.datasets.leads.find((item) => String(item.id) === String(normalizedLeadId));
          if (existingLead) {
            return existingLead;
          }

          const payload = await this.apiRequest(`/api/v1/leads/${normalizedLeadId}/`);
          return this.mapLead(payload);
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
        async fetchCompanyById(companyId) {
          const normalizedCompanyId = this.toIntOrNull(companyId);
          if (!normalizedCompanyId) {
            throw new Error("Некорректный ID компании");
          }

          const existingCompany = (this.datasets.companies || []).find((item) => String(item.id) === String(normalizedCompanyId));
          if (existingCompany) {
            return existingCompany;
          }

          const payload = await this.apiRequest(`/api/v1/clients/${normalizedCompanyId}/`);
          return this.mapClient(payload);
        },
        async openTaskFromEvent(taskId) {
          try {
            const task = await this.fetchTaskById(taskId);
            this.openTaskEditor(task, { parentContext: this.modalParentContext || this.captureModalParentContext() });
          } catch (error) {
            this.errorMessage = `Ошибка открытия задачи: ${error.message}`;
          }
        },
        async openTouchFromEvent(touchId) {
          try {
            const normalizedTouchId = this.toIntOrNull(touchId);
            if (!normalizedTouchId) {
              throw new Error("Касание не найдено");
            }
            const existingTouch = (this.datasets.touches || []).find((item) => String(item.id) === String(normalizedTouchId));
            const touch = existingTouch || this.mapTouch(await this.apiRequest(`/api/v1/touches/${normalizedTouchId}/`));
            this.openTouchEditor(touch, { parentContext: this.modalParentContext || this.captureModalParentContext() });
          } catch (error) {
            this.errorMessage = `Ошибка открытия касания: ${error.message}`;
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
        async fetchConversationById(conversationId) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          if (!normalizedConversationId) {
            throw new Error("Некорректный ID диалога");
          }
          return this.mapConversation(await this.apiRequest(`/api/v1/communications/conversations/${normalizedConversationId}/`));
        },
        async openCommunicationConversationFromEvent(eventItem) {
          const conversationId = this.toIntOrNull(eventItem?.conversationId);
          if (!conversationId) {
            throw new Error("Диалог не найден");
          }
          const conversation = await this.fetchConversationById(conversationId);
          const dealId = this.toIntOrNull(conversation.dealId || eventItem?.dealId);
          const companyId = this.toIntOrNull(
            conversation.clientId
            || this.editingCompanyId
            || this.editingLeadItem?.clientId
            || this.editingDealItem?.clientId
          );

          if (dealId) {
            const deal = await this.fetchDealById(dealId);
            this.openDealEditor(deal);
            this.showDealCommunicationsPanel = true;
            await this.loadDealCommunications({ preserveSelection: false, forceReloadMessages: true });
            await this.selectDealConversation(conversationId, { silent: true });
            this.ensureCommunicationsPolling();
            return;
          }

          if (companyId) {
            const company = await this.fetchCompanyById(companyId);
            this.openCompanyEditor(company);
            this.showCompanyCommunicationsPanel = true;
            await this.loadCompanyCommunications({ preserveSelection: false, forceReloadMessages: true });
            await this.selectCompanyConversation(conversationId, { silent: true });
            this.ensureCommunicationsPolling();
            return;
          }

          throw new Error("Не удалось определить карточку для открытия переписки");
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
          if (typeof data.error === "string" && data.error.trim()) return data.error;
          if (typeof data.message === "string" && data.message.trim()) return data.message;
          if (typeof data.detail === "string") return data.detail;
          const entries = Object.entries(data).filter(([field]) => field !== "ok");
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
        closeCompanyPanels(exceptKey = "") {
          const normalized = String(exceptKey || "");
          this.showCompanyRequisites = normalized === "requisites" ? this.showCompanyRequisites : false;
          this.showCompanySettlementsPanel = normalized === "settlements" ? this.showCompanySettlementsPanel : false;
          this.showCompanyContactsPanel = normalized === "contacts" ? this.showCompanyContactsPanel : false;
          this.showCompanyDocumentsPanel = normalized === "documents" ? this.showCompanyDocumentsPanel : false;
          this.showCompanyPhoneCallHistory = normalized === "phoneCallHistory" ? this.showCompanyPhoneCallHistory : false;
          this.showCompanyCommunicationsPanel = normalized === "communications" ? this.showCompanyCommunicationsPanel : false;
          this.showCompanyWorkRules = normalized === "workRules" ? this.showCompanyWorkRules : false;
          this.showCompanyDealsPanel = normalized === "deals" ? this.showCompanyDealsPanel : false;
          this.showCompanyLeadsPanel = normalized === "leads" ? this.showCompanyLeadsPanel : false;
          if (normalized !== "communications") {
            this.stopCommunicationsPollingIfIdle();
          }
        },
        toggleExclusiveCompanyPanel(panelKey) {
          const normalized = String(panelKey || "");
          const currentState = normalized === "requisites"
            ? this.showCompanyRequisites
            : normalized === "settlements"
              ? this.showCompanySettlementsPanel
            : normalized === "contacts"
              ? this.showCompanyContactsPanel
              : normalized === "documents"
                ? this.showCompanyDocumentsPanel
              : normalized === "phoneCallHistory"
                ? this.showCompanyPhoneCallHistory
              : normalized === "communications"
                ? this.showCompanyCommunicationsPanel
              : normalized === "workRules"
                ? this.showCompanyWorkRules
                : normalized === "deals"
                  ? this.showCompanyDealsPanel
                  : normalized === "leads"
                    ? this.showCompanyLeadsPanel
                    : false;
          this.closeCompanyPanels();
          if (currentState) {
            return;
          }
          if (normalized === "requisites") this.showCompanyRequisites = true;
          if (normalized === "settlements") this.showCompanySettlementsPanel = true;
          if (normalized === "contacts") this.showCompanyContactsPanel = true;
          if (normalized === "documents") this.showCompanyDocumentsPanel = true;
          if (normalized === "phoneCallHistory") this.showCompanyPhoneCallHistory = true;
          if (normalized === "communications") this.showCompanyCommunicationsPanel = true;
          if (normalized === "workRules") this.showCompanyWorkRules = true;
          if (normalized === "deals") this.showCompanyDealsPanel = true;
          if (normalized === "leads") this.showCompanyLeadsPanel = true;
        },
        toggleCompanyRequisites() {
          this.toggleExclusiveCompanyPanel("requisites");
          if (this.showCompanyRequisites) {
            this.scrollPanelIntoView("company-requisites-panel");
          }
        },
        async toggleCompanySettlementsPanel() {
          const wasOpen = this.showCompanySettlementsPanel;
          this.toggleExclusiveCompanyPanel("settlements");
          if (!wasOpen && this.showCompanySettlementsPanel) {
            await this.loadCompanySettlements();
            this.scrollPanelIntoView("company-settlements-panel");
          }
        },
        toggleCompanyWorkRules() {
          this.toggleExclusiveCompanyPanel("workRules");
          if (this.showCompanyWorkRules) {
            this.scrollPanelIntoView("company-workrules-panel");
          }
        },
        async toggleCompanyDocumentsPanel() {
          const wasOpen = this.showCompanyDocumentsPanel;
          this.toggleExclusiveCompanyPanel("documents");
          if (!wasOpen && this.showCompanyDocumentsPanel) {
            await this.loadCompanyDocuments();
            this.scrollPanelIntoView("company-documents-panel");
          }
        },
        async toggleCompanyPhoneCallHistoryPanel() {
          const wasOpen = this.showCompanyPhoneCallHistory;
          this.toggleExclusiveCompanyPanel("phoneCallHistory");
          if (!wasOpen && this.showCompanyPhoneCallHistory) {
            await this.ensurePhoneCallHistoryLoaded("company", this.editingCompanyId);
            this.scrollPanelIntoView("company-phone-history-panel");
          }
        },
        async toggleCompanyCommunicationsPanel() {
          const wasOpen = this.showCompanyCommunicationsPanel;
          this.toggleExclusiveCompanyPanel("communications");
          if (!wasOpen && this.showCompanyCommunicationsPanel) {
            await this.loadCompanyCommunications({ preserveSelection: false });
            this.scrollPanelIntoView("company-communications-panel");
            return;
          }
          if (!this.showCompanyCommunicationsPanel) {
            this.stopCommunicationsPollingIfIdle();
          }
        },
        toggleCompanyDealsPanel() {
          this.toggleExclusiveCompanyPanel("deals");
          if (this.showCompanyDealsPanel) {
            this.scrollPanelIntoView("company-deals-panel");
          }
        },
        toggleCompanyLeadsPanel() {
          this.toggleExclusiveCompanyPanel("leads");
          if (this.showCompanyLeadsPanel) {
            this.scrollPanelIntoView("company-leads-panel");
          }
        },
        settlementDocumentNeedsDirection(documentType) {
          return SETTLEMENT_DIRECTION_REQUIRED_TYPES.includes(String(documentType || "").trim());
        },
        settlementDocumentIsRealization(documentType) {
          return String(documentType || "").trim() === "realization";
        },
        companySettlementDealOptions() {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          return (this.datasets.deals || [])
            .filter((deal) => String(deal.clientId || "") === String(companyId))
            .sort((left, right) => String(left.title || "").localeCompare(String(right.title || ""), "ru"));
        },
        selectedCompanySettlementDeal() {
          const dealId = this.toIntOrNull(this.companySettlementDocumentForm.dealId);
          if (!dealId) {
            return null;
          }
          return (this.datasets.deals || []).find((deal) => String(deal.id) === String(dealId)) || null;
        },
        async ensureCompanySettlementDealsLoaded() {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) {
            return;
          }
          const payload = await this.apiRequest(`/api/v1/deals/?client=${companyId}&page_size=200`);
          const records = this.normalizePaginatedResponse(payload).map((item) => this.mapDeal(item));
          this.datasets.deals = this.mergeSectionRecords(this.datasets.deals, records);
        },
        defaultCompanySettlementDocumentTitle(documentType) {
          return this.settlementDocumentIsRealization(documentType) ? "Акт об оказании услуг" : "";
        },
        normalizeSettlementContract(item = {}) {
          return {
            id: this.toIntOrNull(item.id),
            clientId: this.toIntOrNull(item.client),
            title: item.title || "",
            number: item.number || "",
            currency: item.currency || this.forms.companies.currency || "RUB",
            hourlyRate: Number(item.hourly_rate ?? item.hourlyRate ?? 0) || 0,
            startDate: item.start_date || item.startDate || "",
            endDate: item.end_date || item.endDate || "",
            note: item.note || "",
            isActive: item.is_active !== false,
            createdAt: item.created_at || item.createdAt || "",
            updatedAt: item.updated_at || item.updatedAt || "",
          };
        },
        preferredCompanySettlementContractId() {
          const latestContract = Array.isArray(this.companySettlementContracts) && this.companySettlementContracts.length
            ? this.companySettlementContracts[0]
            : null;
          return this.toIntOrNull(latestContract?.id);
        },
        openNewCompanySettlementContractForm() {
          this.resetCompanySettlementContractForm();
          this.showCompanySettlementContractForm = true;
        },
        async openCompanySettlementContractEditor(contract) {
          const normalizedContract = contract ? this.normalizeSettlementContract(contract) : null;
          if (!normalizedContract?.id) {
            return;
          }
          if (!this.showCompanySettlementsPanel) {
            await this.toggleCompanySettlementsPanel();
          } else if (!this.companySettlementContracts.length) {
            await this.loadCompanySettlements();
          }
          this.companySettlementContractForm = {
            id: normalizedContract.id,
            title: normalizedContract.title || "",
            number: normalizedContract.number || "",
            currency: normalizedContract.currency || this.forms.companies.currency || "RUB",
            hourlyRate: normalizedContract.hourlyRate > 0 ? normalizedContract.hourlyRate.toFixed(2) : "",
            startDate: normalizedContract.startDate || "",
            endDate: normalizedContract.endDate || "",
            note: normalizedContract.note || "",
            isActive: normalizedContract.isActive !== false,
          };
          this.showCompanySettlementContractForm = true;
          this.$nextTick(() => {
            const panel = document.getElementById("company-settlements-panel");
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
        },
        closeCompanySettlementContractForm() {
          this.showCompanySettlementContractForm = false;
          this.resetCompanySettlementContractForm();
        },
        async openCompanySettlementContractSummary(contractId) {
          const normalizedContractId = this.toIntOrNull(contractId);
          if (!normalizedContractId || !this.editingCompanyId) {
            return;
          }
          if (!this.showCompanySettlementsPanel) {
            await this.toggleCompanySettlementsPanel();
          } else if (!this.companySettlementSummary.contracts.length) {
            await this.loadCompanySettlements();
          }
          this.$nextTick(() => {
            const panel = document.getElementById(`company-settlement-contract-card-${normalizedContractId}`);
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
        },
        toggleCompanySettlementDocumentForm() {
          const shouldOpen = !this.showCompanySettlementDocumentForm;
          this.showCompanySettlementDocumentForm = shouldOpen;
          if (!shouldOpen) {
            return;
          }
          this.resetCompanySettlementDocumentForm();
        },
        syncCompanySettlementAmountFromDeal() {
          if (!this.settlementDocumentIsRealization(this.companySettlementDocumentForm.documentType)) {
            return;
          }
          const deal = this.selectedCompanySettlementDeal();
          if (!deal) {
            return;
          }
          const amount = Number(deal.amount || 0);
          if (!Number.isFinite(amount) || amount <= 0) {
            return;
          }
          this.companySettlementDocumentForm.amount = amount.toFixed(2);
        },
        handleCompanySettlementDocumentTypeChange() {
          if (this.settlementDocumentIsRealization(this.companySettlementDocumentForm.documentType)) {
            if (!this.companySettlementDocumentForm.realizationStatus) {
              this.companySettlementDocumentForm.realizationStatus = "created";
            }
            if (!String(this.companySettlementDocumentForm.title || "").trim()) {
              this.companySettlementDocumentForm.title = this.defaultCompanySettlementDocumentTitle(this.companySettlementDocumentForm.documentType);
            }
            this.syncCompanySettlementAmountFromDeal();
            return;
          }
          if (String(this.companySettlementDocumentForm.title || "").trim() === this.defaultCompanySettlementDocumentTitle("realization")) {
            this.companySettlementDocumentForm.title = "";
          }
          this.companySettlementDocumentForm.realizationStatus = "";
        },
        defaultCompanySettlementSummary() {
          return {
            overview: {
              expectedReceivable: 0,
              receivable: 0,
              payable: 0,
              advancesReceived: 0,
              advancesIssued: 0,
              overdue: 0,
              nearestDueDate: "",
              balance: 0,
            },
            contracts: [],
          };
        },
        resetCompanySettlementContractForm() {
          this.companySettlementContractForm = {
            id: null,
            title: "",
            number: "",
            currency: this.forms.companies.currency || "RUB",
            hourlyRate: "",
            startDate: "",
            endDate: "",
            note: "",
            isActive: true,
          };
        },
        resetCompanySettlementDocumentForm() {
          this.companySettlementDocumentForm = {
            contractId: this.preferredCompanySettlementContractId(),
            dealId: null,
            documentType: "invoice",
            flowDirection: "",
            title: this.defaultCompanySettlementDocumentTitle("invoice"),
            documentDate: new Date().toISOString().slice(0, 10),
            dueDate: "",
            amount: "",
            currency: this.forms.companies.currency || "RUB",
            realizationStatus: "",
            note: "",
            file: null,
            fileName: "",
          };
          this.clearCompanySettlementDocumentFileInput();
        },
        resetCompanySettlementAllocationForm() {
          this.companySettlementAllocationForm = {
            sourceDocumentId: null,
            targetDocumentId: null,
            amount: "",
            allocatedAt: new Date().toISOString().slice(0, 10),
            note: "",
          };
        },
        resetCompanySettlementState() {
          this.showCompanySettlementContractForm = false;
          this.showCompanySettlementDocumentForm = false;
          this.showCompanySettlementAllocationForm = false;
          this.isCompanySettlementsLoading = false;
          this.isCompanySettlementSaving = false;
          this.companySettlementContracts = [];
          this.companySettlementDocuments = [];
          this.companySettlementDocumentStatusSaving = {};
          this.companySettlementSummary = this.defaultCompanySettlementSummary();
          this.resetCompanySettlementContractForm();
          this.resetCompanySettlementDocumentForm();
          this.resetCompanySettlementAllocationForm();
        },
        formatSettlementDate(value) {
          if (!value) return "Не указана";
          const date = new Date(value);
          if (Number.isNaN(date.getTime())) return "Не указана";
          return date.toLocaleDateString("ru-RU");
        },
        formatSettlementAmount(amount, currency = "RUB") {
          const numeric = Number(amount || 0);
          const safeCurrency = String(currency || "RUB").trim() || "RUB";
          return `${numeric.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${safeCurrency}`;
        },
        settlementDocumentStatusLabel(document) {
          const openAmount = Number(document?.openAmount || 0);
          const closedAmount = Number(document?.closedAmount || 0);
          if (openAmount <= 0) return "Погашен";
          if (closedAmount > 0) return "Частично погашен";
          return "Не погашен";
        },
        settlementDocumentStatusClass(document) {
          const openAmount = Number(document?.openAmount || 0);
          const closedAmount = Number(document?.closedAmount || 0);
          if (openAmount <= 0) return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
          if (closedAmount > 0) return "border-amber-400/30 bg-amber-400/10 text-amber-200";
          return "border-sky-400/30 bg-sky-400/10 text-sky-200";
        },
        settlementRealizationStatusLabel(document) {
          const status = String(document?.realizationStatus || "created").trim() || "created";
          const option = (this.settlementRealizationStatusOptions || []).find((item) => String(item.value || "") === status);
          return option?.label || "Создан";
        },
        settlementRealizationStatusClass(document) {
          const status = String(document?.realizationStatus || "created").trim() || "created";
          if (status === "signed") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
          if (status === "sent_to_client") return "border-amber-400/30 bg-amber-400/10 text-amber-200";
          return "border-slate-300/25 bg-slate-300/10 text-slate-100";
        },
        nextSettlementRealizationStatus(document) {
          const statusOrder = (this.settlementRealizationStatusOptions || []).map((item) => String(item.value || "")).filter(Boolean);
          if (!statusOrder.length) {
            return "created";
          }
          const currentStatus = String(document?.realizationStatus || "created").trim() || "created";
          const currentIndex = statusOrder.indexOf(currentStatus);
          if (currentIndex === -1 || currentIndex === statusOrder.length - 1) {
            return statusOrder[0];
          }
          return statusOrder[currentIndex + 1];
        },
        settlementHistoryRoleLabel(item) {
          const role = String(item?.historyRole || item?.history_role || "").trim();
          return role === "outgoing" ? "Исходящее распределение" : "Входящее распределение";
        },
        normalizeCompanySettlementSummary(payload = {}) {
          const overview = payload && typeof payload.overview === "object" ? payload.overview : {};
          const contracts = Array.isArray(payload.contracts) ? payload.contracts : [];
          return {
            overview: {
              expectedReceivable: Number(overview.expected_receivable || 0),
              receivable: Number(overview.receivable || 0),
              payable: Number(overview.payable || 0),
              advancesReceived: Number(overview.advances_received || 0),
              advancesIssued: Number(overview.advances_issued || 0),
              overdue: Number(overview.overdue || 0),
              nearestDueDate: overview.nearest_due_date || "",
              balance: Number(overview.balance || 0),
            },
            contracts: contracts.map((contract) => {
              const stats = contract && typeof contract.stats === "object" ? contract.stats : {};
              return {
                contractId: this.toIntOrNull(contract.contract_id),
                title: contract.title || "Без договора",
                number: contract.number || "",
                currency: contract.currency || this.forms.companies.currency || "RUB",
                hourlyRate: Number(contract.hourly_rate || 0) || 0,
                documentsCount: Number(contract.documents_count || 0),
                stats: {
                  expectedReceivable: Number(stats.expected_receivable || 0),
                  receivable: Number(stats.receivable || 0),
                  payable: Number(stats.payable || 0),
                  advancesReceived: Number(stats.advances_received || 0),
                  advancesIssued: Number(stats.advances_issued || 0),
                  overdue: Number(stats.overdue || 0),
                  nearestDueDate: stats.nearest_due_date || "",
                  balance: Number(stats.balance || 0),
                },
              };
            }),
          };
        },
        normalizeCompanySettlementDocument(item = {}) {
          return {
            id: this.toIntOrNull(item.id),
            clientId: this.toIntOrNull(item.client),
            contractId: this.toIntOrNull(item.contract),
            contractName: item.contract_name || "Без договора",
            dealId: this.toIntOrNull(item.deal),
            dealTitle: item.deal_title || "",
            documentType: item.document_type || "",
            documentTypeLabel: item.document_type_label || "",
            flowDirection: item.flow_direction || "",
            flowDirectionLabel: item.flow_direction_label || "",
            realizationStatus: item.realization_status || "",
            realizationStatusLabel: item.realization_status_label || "",
            title: item.title || "",
            number: item.number || "",
            documentDate: item.document_date || "",
            dueDate: item.due_date || "",
            currency: item.currency || this.forms.companies.currency || "RUB",
            amount: Number(item.amount || 0),
            openAmount: Number(item.open_amount || 0),
            closedAmount: Number(item.closed_amount || 0),
            note: item.note || "",
            originalName: item.original_name || item.originalName || "",
            fileUrl: item.download_url || item.downloadUrl || item.file_url || item.fileUrl || "",
            fileSize: Number.parseInt(item.file_size || item.fileSize || 0, 10) || 0,
            canAllocateAsSource: !!item.can_allocate_as_source,
            canAllocateAsTarget: !!item.can_allocate_as_target,
            allocationHistory: Array.isArray(item.allocation_history)
              ? item.allocation_history.map((entry) => ({
                id: this.toIntOrNull(entry.id),
                historyRole: entry.history_role || "",
                amount: Number(entry.amount || 0),
                allocatedAt: entry.allocated_at || "",
                note: entry.note || "",
                sourceDocumentId: this.toIntOrNull(entry.source_document_id),
                sourceDocumentTypeLabel: entry.source_document_type_label || "",
                sourceDocumentNumber: entry.source_document_number || "",
                sourceDocumentTitle: entry.source_document_title || "",
                targetDocumentId: this.toIntOrNull(entry.target_document_id),
                targetDocumentTypeLabel: entry.target_document_type_label || "",
                targetDocumentNumber: entry.target_document_number || "",
                targetDocumentTitle: entry.target_document_title || "",
              }))
              : [],
          };
        },
        handleCompanySettlementDocumentFileInput(event) {
          const input = event?.target;
          const file = input?.files && input.files[0] ? input.files[0] : null;
          this.companySettlementDocumentForm.file = file;
          this.companySettlementDocumentForm.fileName = file?.name || "";
        },
        isCompanySettlementDocumentStatusSaving(documentId) {
          return !!this.companySettlementDocumentStatusSaving[String(this.toIntOrNull(documentId) || "")];
        },
        clearCompanySettlementDocumentFileInput() {
          const input = this.$refs.companySettlementDocumentFileInput;
          if (input) {
            input.value = "";
          }
        },
        async updateCompanySettlementRealizationStatus(document, nextStatus) {
          const documentId = this.toIntOrNull(document?.id);
          const normalizedStatus = String(nextStatus || "").trim();
          if (!documentId || !normalizedStatus || String(document?.documentType || "") !== "realization") {
            return;
          }
          if (String(document.realizationStatus || "") === normalizedStatus) {
            return;
          }
          this.companySettlementDocumentStatusSaving = {
            ...this.companySettlementDocumentStatusSaving,
            [String(documentId)]: true,
          };
          this.clearUiErrors({ modalOnly: true });
          try {
            const updated = await this.apiRequest(`/api/v1/settlements/documents/${documentId}/`, {
              method: "PATCH",
              body: {
                realization_status: normalizedStatus,
              },
            });
            const normalizedDocument = this.normalizeCompanySettlementDocument(updated);
            this.companySettlementDocuments = this.companySettlementDocuments.map((item) => (
              this.toIntOrNull(item.id) === documentId ? { ...item, ...normalizedDocument } : item
            ));
          } catch (error) {
            this.setUiError(`Ошибка обновления статуса акта: ${error.message}`, { modal: true });
          } finally {
            const nextSavingState = { ...this.companySettlementDocumentStatusSaving };
            delete nextSavingState[String(documentId)];
            this.companySettlementDocumentStatusSaving = nextSavingState;
          }
        },
        async cycleCompanySettlementRealizationStatus(document) {
          if (String(document?.documentType || "") !== "realization") {
            return;
          }
          if (this.isCompanySettlementDocumentStatusSaving(document?.id)) {
            return;
          }
          await this.updateCompanySettlementRealizationStatus(document, this.nextSettlementRealizationStatus(document));
        },
        companySettlementSourceDocuments() {
          return (this.companySettlementDocuments || []).filter((item) => item.canAllocateAsSource && Number(item.openAmount || 0) > 0);
        },
        companySettlementTargetDocuments() {
          return (this.companySettlementDocuments || []).filter((item) => item.canAllocateAsTarget && Number(item.openAmount || 0) > 0);
        },
        async loadCompanySettlements() {
          if (!this.editingCompanyId) {
            this.companySettlementContracts = [];
            this.companySettlementDocuments = [];
            this.companySettlementSummary = this.defaultCompanySettlementSummary();
            return;
          }
          this.isCompanySettlementsLoading = true;
          try {
            await this.ensureCompanySettlementDealsLoaded();
            const [summaryPayload, contractsPayload, documentsPayload] = await Promise.all([
              this.apiRequest(`/api/v1/settlements/summary/?client=${this.editingCompanyId}`),
              this.apiRequest(`/api/v1/settlements/contracts/?client=${this.editingCompanyId}&page_size=100`),
              this.apiRequest(`/api/v1/settlements/documents/?client=${this.editingCompanyId}&page_size=200`),
            ]);
            const normalizedSummary = this.normalizeCompanySettlementSummary(summaryPayload);
            this.companySettlementContracts = this.normalizePaginatedResponse(contractsPayload).map((item) => this.normalizeSettlementContract(item));
            const contractsById = new Map(
              (this.companySettlementContracts || [])
                .filter((contract) => this.toIntOrNull(contract.id))
                .map((contract) => [this.toIntOrNull(contract.id), contract])
            );
            const existingContractIds = new Set(
              (normalizedSummary.contracts || [])
                .map((item) => this.toIntOrNull(item.contractId))
                .filter(Boolean)
            );
            const emptyContracts = this.companySettlementContracts
              .filter((contract) => !existingContractIds.has(this.toIntOrNull(contract.id)))
              .map((contract) => ({
                contractId: this.toIntOrNull(contract.id),
                title: contract.title || contract.number || `Договор #${contract.id}`,
                number: contract.number || "",
                currency: contract.currency || this.forms.companies.currency || "RUB",
                hourlyRate: Number(contract.hourlyRate || 0) || 0,
                documentsCount: 0,
                stats: {
                  receivable: 0,
                  payable: 0,
                  expectedReceivable: 0,
                  advancesReceived: 0,
                  advancesIssued: 0,
                  overdue: 0,
                  nearestDueDate: "",
                  balance: 0,
                },
              }));
            this.companySettlementSummary = {
              ...normalizedSummary,
              contracts: [...(normalizedSummary.contracts || []), ...emptyContracts]
                .map((contract) => {
                  const normalizedContractId = this.toIntOrNull(contract.contractId);
                  const linkedContract = normalizedContractId ? contractsById.get(normalizedContractId) : null;
                  return {
                    ...contract,
                    title: linkedContract?.title || contract.title,
                    number: linkedContract?.number || contract.number,
                    currency: linkedContract?.currency || contract.currency,
                    hourlyRate: Number(linkedContract?.hourlyRate || contract.hourlyRate || 0) || 0,
                    isActive: linkedContract ? linkedContract.isActive !== false : true,
                  };
                })
                .sort((left, right) => (
                String(left.title || "").localeCompare(String(right.title || ""), "ru")
              )),
            };
            this.companySettlementDocuments = this.normalizePaginatedResponse(documentsPayload).map((item) => this.normalizeCompanySettlementDocument(item));
          } catch (error) {
            this.setUiError(`Ошибка загрузки взаиморасчетов: ${error.message}`, { modal: true });
            this.companySettlementSummary = this.defaultCompanySettlementSummary();
            this.companySettlementContracts = [];
            this.companySettlementDocuments = [];
          } finally {
            this.isCompanySettlementsLoading = false;
          }
        },
        async saveCompanySettlementContract() {
          if (!this.editingCompanyId) {
            throw new Error("Сначала откройте компанию");
          }
          this.isCompanySettlementSaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            const contractId = this.toIntOrNull(this.companySettlementContractForm.id);
            const hourlyRate = this.parseFlexibleNumber(this.companySettlementContractForm.hourlyRate);
            await this.apiRequest(contractId ? `/api/v1/settlements/contracts/${contractId}/` : "/api/v1/settlements/contracts/", {
              method: contractId ? "PATCH" : "POST",
              body: {
                client: this.editingCompanyId,
                title: this.companySettlementContractForm.title.trim(),
                number: this.companySettlementContractForm.number.trim(),
                currency: this.companySettlementContractForm.currency || this.forms.companies.currency || "RUB",
                hourly_rate: hourlyRate > 0 ? hourlyRate.toFixed(2) : null,
                start_date: this.companySettlementContractForm.startDate || null,
                end_date: this.companySettlementContractForm.endDate || null,
                note: this.companySettlementContractForm.note.trim(),
                is_active: !!this.companySettlementContractForm.isActive,
              },
            });
            this.closeCompanySettlementContractForm();
            await this.loadCompanySettlements();
            if (this.showCompanyDocumentsPanel) {
              await this.loadCompanyDocuments();
            }
          } catch (error) {
            const actionLabel = this.toIntOrNull(this.companySettlementContractForm.id) ? "обновления" : "создания";
            this.setUiError(`Ошибка ${actionLabel} договора: ${error.message}`, { modal: true });
          } finally {
            this.isCompanySettlementSaving = false;
          }
        },
        async createCompanySettlementDocument() {
          if (!this.editingCompanyId) {
            throw new Error("Сначала откройте компанию");
          }
          const amount = Number(this.companySettlementDocumentForm.amount || 0);
          const dealId = this.toIntOrNull(this.companySettlementDocumentForm.dealId);
          if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error("Укажите сумму документа больше нуля");
          }
          if (this.settlementDocumentIsRealization(this.companySettlementDocumentForm.documentType) && !dealId) {
            throw new Error("Для акта нужно выбрать сделку");
          }
          if (this.settlementDocumentNeedsDirection(this.companySettlementDocumentForm.documentType) && !this.companySettlementDocumentForm.flowDirection) {
            throw new Error("Укажите направление документа");
          }
          this.isCompanySettlementSaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            const file = this.companySettlementDocumentForm.file || null;
            const contractId = this.toIntOrNull(this.companySettlementDocumentForm.contractId);
            let createdDocument = null;
            const payload = {
              client: this.editingCompanyId,
              contract: contractId,
              deal: dealId,
              document_type: this.companySettlementDocumentForm.documentType,
              flow_direction: this.settlementDocumentNeedsDirection(this.companySettlementDocumentForm.documentType)
                ? this.companySettlementDocumentForm.flowDirection
                : "",
              realization_status: this.settlementDocumentIsRealization(this.companySettlementDocumentForm.documentType)
                ? (this.companySettlementDocumentForm.realizationStatus || "created")
                : "",
              title: this.companySettlementDocumentForm.title.trim(),
              number: "",
              document_date: this.companySettlementDocumentForm.documentDate || new Date().toISOString().slice(0, 10),
              due_date: this.companySettlementDocumentForm.dueDate || null,
              currency: this.companySettlementDocumentForm.currency || this.forms.companies.currency || "RUB",
              amount: amount.toFixed(2),
              note: this.companySettlementDocumentForm.note.trim(),
            };
            if (file) {
              const formData = new FormData();
              formData.append("client", String(this.editingCompanyId));
              if (contractId) {
                formData.append("contract", String(contractId));
              }
              if (dealId) {
                formData.append("deal", String(dealId));
              }
              formData.append("document_type", payload.document_type);
              formData.append("flow_direction", payload.flow_direction || "");
              formData.append("realization_status", payload.realization_status || "");
              formData.append("title", payload.title);
              formData.append("number", payload.number);
              formData.append("document_date", payload.document_date);
              if (payload.due_date) {
                formData.append("due_date", payload.due_date);
              }
              formData.append("currency", payload.currency);
              formData.append("amount", payload.amount);
              formData.append("note", payload.note);
              formData.append("file", file);
              formData.append("original_name", this.companySettlementDocumentForm.fileName || file.name || "");
              createdDocument = await this.apiRequest("/api/v1/settlements/documents/", {
                method: "POST",
                body: formData,
              });
            } else {
              createdDocument = await this.apiRequest("/api/v1/settlements/documents/", {
                method: "POST",
                body: payload,
              });
            }
            this.resetCompanySettlementDocumentForm();
            this.showCompanySettlementDocumentForm = false;
            await this.loadCompanySettlements();
            if (createdDocument) {
              const normalizedCreatedDocument = this.normalizeCompanySettlementDocument(createdDocument);
              if (!this.companySettlementDocuments.some((item) => this.toIntOrNull(item.id) === this.toIntOrNull(normalizedCreatedDocument.id))) {
                this.companySettlementDocuments = [normalizedCreatedDocument, ...this.companySettlementDocuments];
              }
            }
          } catch (error) {
            this.setUiError(`Ошибка создания документа: ${error.message}`, { modal: true });
          } finally {
            this.isCompanySettlementSaving = false;
          }
        },
        async createCompanySettlementAllocation() {
          if (!this.editingCompanyId) {
            throw new Error("Сначала откройте компанию");
          }
          const amount = Number(this.companySettlementAllocationForm.amount || 0);
          const sourceDocumentId = this.toIntOrNull(this.companySettlementAllocationForm.sourceDocumentId);
          const targetDocumentId = this.toIntOrNull(this.companySettlementAllocationForm.targetDocumentId);
          if (!sourceDocumentId || !targetDocumentId) {
            throw new Error("Выберите документы источника и закрытия");
          }
          if (sourceDocumentId === targetDocumentId) {
            throw new Error("Источник и закрываемый документ должны различаться");
          }
          if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error("Укажите сумму закрытия больше нуля");
          }
          this.isCompanySettlementSaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.apiRequest("/api/v1/settlements/allocations/", {
              method: "POST",
              body: {
                source_document: sourceDocumentId,
                target_document: targetDocumentId,
                amount: amount.toFixed(2),
                allocated_at: this.companySettlementAllocationForm.allocatedAt || new Date().toISOString().slice(0, 10),
                note: this.companySettlementAllocationForm.note.trim(),
              },
            });
            this.resetCompanySettlementAllocationForm();
            this.showCompanySettlementAllocationForm = false;
            await this.loadCompanySettlements();
          } catch (error) {
            this.setUiError(`Ошибка закрытия документа: ${error.message}`, { modal: true });
          } finally {
            this.isCompanySettlementSaving = false;
          }
        },
        communicationChannelLabel(value) {
          const code = String(value || "").trim().toLowerCase();
          if (!code) return "Сообщение";
          if (code === "email") return "Email";
          if (code === "telegram") return "Telegram";
          return code;
        },
        communicationMessageStatusLabel(value) {
          const code = String(value || "").trim().toLowerCase();
          const labels = {
            draft: "Черновик",
            queued: "В очереди",
            sending: "Отправляется",
            sent: "Отправлено",
            delivered: "Доставлено",
            received: "Получено",
            failed: "Ошибка",
            requires_manual_retry: "Нужен ручной retry",
          };
          return labels[code] || "Без статуса";
        },
        communicationMessageStatusClass(value) {
          const code = String(value || "").trim().toLowerCase();
          if (code === "sent" || code === "delivered") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
          if (code === "queued" || code === "sending") return "border-amber-400/30 bg-amber-400/10 text-amber-200";
          if (code === "failed" || code === "requires_manual_retry") return "border-red-400/30 bg-red-400/10 text-red-200";
          return "border-crm-border bg-[#12324e] text-crm-text";
        },
        communicationMessageDirectionLabel(value) {
          return String(value || "").trim().toLowerCase() === "incoming" ? "Входящее" : "Исходящее";
        },
        mapConversation(item) {
          return {
            id: this.toIntOrNull(item.id),
            channel: String(item.channel || "").trim().toLowerCase(),
            channelLabel: this.communicationChannelLabel(item.channel),
            subject: item.subject || "",
            status: item.status || "",
            clientId: this.toIntOrNull(item.client),
            clientName: item.client_name || "",
            contactId: this.toIntOrNull(item.contact),
            contactName: item.contact_name || "",
            dealId: this.toIntOrNull(item.deal),
            dealTitle: item.deal_title || "",
            requiresManualBinding: !!item.requires_manual_binding,
            lastMessageId: this.toIntOrNull(item.last_message_id),
            lastMessageDirection: item.last_message_direction || "",
            lastMessagePreview: item.last_message_preview || "",
            lastMessageAt: item.last_message_at || "",
            lastIncomingAt: item.last_incoming_at || "",
            lastOutgoingAt: item.last_outgoing_at || "",
            createdAt: item.created_at || "",
            updatedAt: item.updated_at || "",
          };
        },
        mapCommunicationMessage(item) {
          return {
            id: this.toIntOrNull(item.id),
            conversationId: this.toIntOrNull(item.conversation),
            channel: String(item.channel || "").trim().toLowerCase(),
            direction: String(item.direction || "").trim().toLowerCase(),
            directionLabel: this.communicationMessageDirectionLabel(item.direction),
            status: item.status || "",
            statusLabel: this.communicationMessageStatusLabel(item.status),
            subject: item.subject || "",
            bodyText: item.body_text || "",
            bodyHtml: item.body_html || "",
            bodyPreview: item.body_preview || "",
            sentAt: item.sent_at || "",
            receivedAt: item.received_at || "",
            deliveredAt: item.delivered_at || "",
            createdAt: item.created_at || "",
            externalSenderKey: item.external_sender_key || "",
            externalRecipientKey: item.external_recipient_key || "",
            contactName: item.contact_name || "",
            dealTitle: item.deal_title || "",
            clientName: item.client_name || "",
            lastErrorMessage: item.last_error_message || "",
            requiresManualRetry: !!item.requires_manual_retry,
            attachments: Array.isArray(item.attachments) ? item.attachments.map((attachment) => ({
              id: this.toIntOrNull(attachment.id),
              originalName: attachment.original_name || "",
              mimeType: attachment.mime_type || "",
              sizeBytes: Number.parseInt(attachment.size_bytes || 0, 10) || 0,
              fileUrl: attachment.file_url || "",
            })) : [],
          };
        },
        mapCommunicationsTimelineMessage(item) {
          const message = this.mapCommunicationMessage(item);
          return {
            ...message,
            timelineType: "message",
            timelineChannel: message.channel,
            timelineAt: message.receivedAt || message.sentAt || message.deliveredAt || message.createdAt || "",
            timelineKey: `message-${message.id}`,
          };
        },
        mapCommunicationsTimelineCall(item) {
          const direction = String(item.direction || "").trim().toLowerCase();
          const status = String(item.status || "").trim().toLowerCase();
          const displayPhone = direction === "inbound"
            ? String(item.phone_from || item.client_phone_normalized || "").trim()
            : String(item.phone_to || item.client_phone_normalized || "").trim();
          return {
            id: this.toIntOrNull(item.id),
            timelineType: "call",
            timelineChannel: "calls",
            timelineAt: item.started_at || item.created_at || "",
            timelineKey: `call-${item.id}`,
            direction,
            status,
            statusLabel: ({
              ringing: "Звонит",
              answered: "Отвечен",
              missed: "Пропущен",
              completed: "Завершен",
              failed: "Ошибка",
              canceled: "Отменен",
            })[status] || "Звонок",
            displayPhone,
            phoneFrom: String(item.phone_from || "").trim(),
            phoneTo: String(item.phone_to || "").trim(),
            recordingUrl: String(item.recording_url || "").trim(),
            durationSec: Number.parseInt(item.duration_sec || 0, 10) || 0,
            talkDurationSec: Number.parseInt(item.talk_duration_sec || 0, 10) || 0,
            startedAt: item.started_at || "",
            answeredAt: item.answered_at || "",
            endedAt: item.ended_at || "",
            responsibleUserName: String(item.responsible_user_name || "").trim(),
            contactName: String(item.contact_name || "").trim(),
            dealTitle: String(item.deal_title || "").trim(),
            rawPayload: item.raw_payload_last && typeof item.raw_payload_last === "object" ? item.raw_payload_last : {},
          };
        },
        communicationsTimelineFilterButtonClass(value) {
          const normalized = String(value || "all").trim().toLowerCase();
          const isActive = normalized === String(this.communicationsTimelineFilter || "all").trim().toLowerCase();
          return isActive
            ? "border-crm-accent bg-crm-accent/15 text-white"
            : "border-crm-border bg-[#123753] text-crm-muted hover:border-crm-accent/70 hover:text-white";
        },
        communicationsTimelineItemTitle(item) {
          if (!item || typeof item !== "object") {
            return "Событие";
          }
          if (item.timelineType === "call") {
            return item.displayPhone || "Звонок";
          }
          return item.subject || item.contactName || item.clientName || item.bodyPreview || `Сообщение #${item.id}`;
        },
        communicationsTimelineItemSubtitle(item) {
          if (!item || typeof item !== "object") {
            return "";
          }
          if (item.timelineType === "call") {
            const parts = [item.statusLabel];
            if (item.responsibleUserName) {
              parts.push(item.responsibleUserName);
            }
            if (item.dealTitle) {
              parts.push(item.dealTitle);
            }
            return parts.filter(Boolean).join(" · ");
          }
          const parts = [
            item.directionLabel,
            item.statusLabel,
            item.contactName || item.clientName,
          ];
          return parts.filter(Boolean).join(" · ");
        },
        communicationsTimelineItemPreview(item) {
          if (!item || typeof item !== "object") {
            return "";
          }
          if (item.timelineType === "call") {
            const parts = [];
            if (item.phoneFrom) parts.push(`От: ${item.phoneFrom}`);
            if (item.phoneTo) parts.push(`Кому: ${item.phoneTo}`);
            if (item.talkDurationSec) parts.push(`Разговор: ${this.formatPhoneCallDuration(item.talkDurationSec)}`);
            else if (item.durationSec) parts.push(`Длительность: ${this.formatPhoneCallDuration(item.durationSec)}`);
            return parts.join(" · ");
          }
          return item.bodyPreview || this.communicationMessagePlainText(item) || "Без текста";
        },
        communicationsTimelineBadgeClass(item) {
          if (item?.timelineType === "call") {
            const status = String(item.status || "").trim().toLowerCase();
            if (status === "completed" || status === "answered") return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
            if (status === "missed" || status === "failed" || status === "canceled") return "border-red-400/30 bg-red-400/10 text-red-200";
            return "border-amber-400/30 bg-amber-400/10 text-amber-200";
          }
          return this.communicationMessageStatusClass(item?.status);
        },
        communicationsTimelineChannelLabel(item) {
          if (item?.timelineType === "call") {
            return "Звонок";
          }
          return this.communicationChannelLabel(item?.channel);
        },
        communicationMessagePlainText(message) {
          const bodyText = String(message?.bodyText || "").trim();
          if (bodyText) {
            return bodyText;
          }
          return this.htmlToPlainText(message?.bodyHtml || "");
        },
        htmlToPlainText(value) {
          const raw = String(value || "").trim();
          if (!raw) return "";
          if (typeof window !== "undefined" && typeof window.DOMParser !== "undefined") {
            const parsed = new window.DOMParser().parseFromString(raw, "text/html");
            return String(parsed.body?.textContent || "").trim();
          }
          return raw.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
        },
        formatPhoneCallDuration(seconds) {
          const totalSeconds = Math.max(0, Number.parseInt(seconds || 0, 10) || 0);
          const minutes = Math.floor(totalSeconds / 60);
          const remainder = totalSeconds % 60;
          if (!minutes) {
            return `${remainder} сек`;
          }
          return `${minutes} мин ${String(remainder).padStart(2, "0")} сек`;
        },
        getDefaultCommunicationsComposer(mode = "email") {
          const normalizedMode = String(mode || "email").trim().toLowerCase();
          const preferredContact = (this.communicationsCompanyContactOptions || []).find((contact) => (
            normalizedMode === "telegram"
              ? !!String(contact.telegram || "").trim()
              : !!String(contact.email || "").trim()
          )) || this.communicationsCompanyContactOptions[0] || null;
          const contactId = this.toIntOrNull(preferredContact?.id);
          const pendingDocumentName = this.communicationsPendingDocumentName;
          return {
            contactId,
            recipient: this.resolveCommunicationsRecipient(normalizedMode, contactId),
            subject: normalizedMode === "email"
              ? (pendingDocumentName || `По компании: ${this.selectedCommunicationsCompany?.name || ""}`.trim())
              : "",
            bodyText: pendingDocumentName ? `Направляю ссылку на ${pendingDocumentName}.` : "",
          };
        },
        resolveCommunicationsRecipient(channelCode, contactId) {
          const normalizedChannel = String(channelCode || "").trim().toLowerCase();
          const normalizedContactId = this.toIntOrNull(contactId);
          const contact = normalizedContactId
            ? ((this.communicationsCompanyContactOptions || []).find((item) => String(item.id) === String(normalizedContactId)) || null)
            : null;
          if (normalizedChannel === "telegram") {
            const contactTelegram = String(contact?.telegram || "").trim();
            return contactTelegram ? `telegram:${contactTelegram}` : "";
          }
          const contactEmail = String(contact?.email || "").trim();
          if (contactEmail) {
            return `email:${contactEmail}`;
          }
          const companyEmail = String(this.selectedCommunicationsCompany?.email || "").trim();
          return companyEmail ? `email:${companyEmail}` : "";
        },
        syncCommunicationsComposerRecipient() {
          if (!this.communicationsComposerMode) {
            return;
          }
          this.communicationsComposer = {
            ...this.communicationsComposer,
            recipient: this.resolveCommunicationsRecipient(this.communicationsComposerMode, this.communicationsComposer.contactId),
          };
        },
        getLatestCommunicationsConversation(channelCode) {
          const normalizedChannel = String(channelCode || "").trim().toLowerCase();
          return (this.communicationsConversations || [])
            .filter((item) => String(item.channel || "").trim().toLowerCase() === normalizedChannel)
            .slice()
            .sort((left, right) => (
              (this.parseTaskDueTimestamp(right.lastMessageAt || right.updatedAt || right.createdAt) || 0)
              - (this.parseTaskDueTimestamp(left.lastMessageAt || left.updatedAt || left.createdAt) || 0)
            ))[0] || null;
        },
        async loadCommunicationsCompanies(force = false) {
          if (this.isCommunicationsCompaniesLoading) {
            return;
          }
          if (!force && this.communicationsCompanies.length) {
            return;
          }
          this.isCommunicationsCompaniesLoading = true;
          try {
            const [companiesPayload, dealsPayload] = await Promise.all([
              this.apiRequest("/api/v1/clients/?company_type=client&page_size=500"),
              this.apiRequest("/api/v1/deals/?page_size=500"),
            ]);
            this.communicationsCompanies = this.normalizePaginatedResponse(companiesPayload).map((item) => this.mapClient(item));
            this.communicationsDeals = this.normalizePaginatedResponse(dealsPayload).map((item) => this.mapDeal(item));
          } finally {
            this.isCommunicationsCompaniesLoading = false;
          }
        },
        async ensureCommunicationsCompanySelection(options = {}) {
          const preserveSelection = !!options.preserveSelection;
          const selectedCompanyId = this.toIntOrNull(this.communicationsSelectedCompanyId);
          const visibleCompanies = this.communicationsVisibleCompanies || [];
          const hasSelectedVisibleCompany = !!selectedCompanyId && visibleCompanies.some(
            (company) => String(company.id) === String(selectedCompanyId)
          );

          if (!visibleCompanies.length) {
            this.communicationsSelectedCompanyId = null;
            this.communicationsContacts = [];
            this.communicationsConversations = [];
            this.communicationsMessages = [];
            this.communicationsCalls = [];
            this.communicationsSelectedTimelineItemKey = "";
            return;
          }

          if (hasSelectedVisibleCompany) {
            if (preserveSelection) {
              await this.selectCommunicationsCompany(selectedCompanyId, { preserveSelection: true });
            }
            return;
          }

          await this.selectCommunicationsCompany(visibleCompanies[0].id);
        },
        async loadCommunicationsContacts(companyId) {
          const normalizedCompanyId = this.toIntOrNull(companyId);
          if (!normalizedCompanyId) {
            this.communicationsContacts = [];
            return;
          }
          this.isCommunicationsContactsLoading = true;
          try {
            const payload = await this.apiRequest(`/api/v1/contacts/?client=${normalizedCompanyId}&page_size=100`);
            this.communicationsContacts = this.normalizePaginatedResponse(payload).map((item) => this.mapContact(item));
          } finally {
            this.isCommunicationsContactsLoading = false;
          }
        },
        async loadCommunicationsTimeline(companyId, options = {}) {
          const normalizedCompanyId = this.toIntOrNull(companyId);
          if (!normalizedCompanyId) {
            this.communicationsConversations = [];
            this.communicationsMessages = [];
            this.communicationsCalls = [];
            this.communicationsSelectedTimelineItemKey = "";
            return;
          }
          const previousSelection = String(this.communicationsSelectedTimelineItemKey || "").trim();
          this.isCommunicationsTimelineLoading = true;
          try {
            const [conversationsPayload, messagesPayload, callsPayload] = await Promise.all([
              this.apiRequest(`/api/v1/communications/conversations/?client=${normalizedCompanyId}&page_size=100`),
              this.apiRequest(`/api/v1/communications/messages/?client=${normalizedCompanyId}&page_size=200`),
              this.apiRequest(`/api/telephony/calls/?entity_type=company&entity_id=${normalizedCompanyId}&page_size=100`),
            ]);
            this.communicationsConversations = this.normalizePaginatedResponse(conversationsPayload).map((item) => this.mapConversation(item));
            this.communicationsMessages = this.normalizePaginatedResponse(messagesPayload).map((item) => this.mapCommunicationsTimelineMessage(item));
            this.communicationsCalls = this.normalizePaginatedResponse(callsPayload).map((item) => this.mapCommunicationsTimelineCall(item));
            if (options.preserveSelection && previousSelection && this.communicationsFilteredTimelineItems.some((item) => item.timelineKey === previousSelection)) {
              this.communicationsSelectedTimelineItemKey = previousSelection;
            } else {
              this.communicationsSelectedTimelineItemKey = this.communicationsFilteredTimelineItems[0]?.timelineKey || "";
            }
          } finally {
            this.isCommunicationsTimelineLoading = false;
          }
        },
        async selectCommunicationsCompany(companyId, options = {}) {
          const normalizedCompanyId = this.toIntOrNull(companyId);
          this.communicationsSelectedCompanyId = normalizedCompanyId;
          this.communicationsSelectedTimelineItemKey = "";
          this.communicationsComposerMode = "";
          if (!normalizedCompanyId) {
            this.communicationsContacts = [];
            this.communicationsConversations = [];
            this.communicationsMessages = [];
            this.communicationsCalls = [];
            return;
          }
          await Promise.all([
            this.loadCommunicationsContacts(normalizedCompanyId),
            this.loadCommunicationsTimeline(normalizedCompanyId, { preserveSelection: !!options.preserveSelection }),
          ]);
          if (options.composeMode) {
            this.openCommunicationsCompose(options.composeMode);
          }
        },
        openCommunicationsCompose(mode) {
          if (!this.toIntOrNull(this.communicationsSelectedCompanyId)) {
            return;
          }
          const normalizedMode = String(mode || "email").trim().toLowerCase();
          this.communicationsComposerMode = normalizedMode;
          this.communicationsComposer = this.getDefaultCommunicationsComposer(normalizedMode);
        },
        closeCommunicationsCompose() {
          this.communicationsComposerMode = "";
          this.communicationsComposer = {
            contactId: null,
            recipient: "",
            subject: "",
            bodyText: "",
          };
        },
        clearCommunicationsPendingDocument() {
          this.communicationsPendingDealDocument = null;
          this.communicationsContextDealId = null;
        },
        async sendCommunicationsMessage() {
          const companyId = this.toIntOrNull(this.communicationsSelectedCompanyId);
          const channel = String(this.communicationsComposerMode || "").trim().toLowerCase();
          if (!companyId || !channel || this.isCommunicationsSending) {
            return;
          }
          this.clearUiErrors({ modalOnly: true });
          this.isCommunicationsSending = true;
          try {
            if (this.communicationsPendingDealDocument && channel !== "email") {
              throw new Error("Ссылку на счет или акт сейчас можно отправить только по email.");
            }
            const recipient = String(this.communicationsComposer.recipient || "").trim();
            if (!recipient) {
              throw new Error(channel === "telegram" ? "Укажите telegram получателя." : "Укажите email получателя.");
            }
            const contactId = this.toIntOrNull(this.communicationsComposer.contactId);
            const pendingDocumentId = this.toIntOrNull(this.communicationsPendingDealDocument?.id);
            const pendingDocumentName = this.communicationsPendingDocumentName || "Документ";
            const payload = {
              recipient,
              subject: channel === "email" ? String(this.communicationsComposer.subject || "").trim() : "",
              body_text: String(this.communicationsComposer.bodyText || "").trim(),
            };
            if (pendingDocumentId) {
              payload.deal_document = pendingDocumentId;
              payload.touch_result_code = "proposal_sent";
              payload.touch_summary = `Отправлен документ: ${this.communicationsPendingDealDocument.originalName || pendingDocumentName}`;
            }

            const existingConversation = this.getLatestCommunicationsConversation(channel);
            let response = null;
            if (existingConversation?.id) {
              response = await this.apiRequest(`/api/v1/communications/conversations/${existingConversation.id}/send/`, {
                method: "POST",
                body: payload,
              });
            } else {
              response = await this.apiRequest("/api/v1/communications/conversations/start/", {
                method: "POST",
                body: {
                  channel,
                  client: companyId,
                  contact: contactId,
                  deal: this.toIntOrNull(this.communicationsContextDealId),
                  recipient,
                  subject: payload.subject,
                  body_text: payload.body_text,
                  ...(pendingDocumentId ? {
                    deal_document: pendingDocumentId,
                    touch_result_code: payload.touch_result_code,
                    touch_summary: payload.touch_summary,
                  } : {}),
                },
              });
            }
            this.ensureOutgoingMessageDelivered(response, channel === "telegram" ? "Сообщение" : "Письмо");
            const sentMessageId = this.toIntOrNull(response?.id || response?.message?.id);
            await this.loadCommunicationsTimeline(companyId, { preserveSelection: false });
            if (sentMessageId) {
              this.communicationsSelectedTimelineItemKey = `message-${sentMessageId}`;
            }
            this.closeCommunicationsCompose();
            this.clearCommunicationsPendingDocument();
          } catch (error) {
            this.setUiError(`Ошибка отправки: ${error.message}`, { modal: true });
          } finally {
            this.isCommunicationsSending = false;
          }
        },
        async openCommunicationsSection(options = {}) {
          const normalizedCompanyId = this.toIntOrNull(options.companyId);
          const composeMode = String(options.composeMode || "").trim().toLowerCase();
          const pendingDocument = options.pendingDocument && typeof options.pendingDocument === "object"
            ? options.pendingDocument
            : null;

          this.setSection("communications");
          if (pendingDocument) {
            this.communicationsPendingDealDocument = pendingDocument;
            this.communicationsContextDealId = this.toIntOrNull(options.dealId || pendingDocument.dealId);
          }
          await this.loadCommunicationsCompanies();
          let targetCompanyId = normalizedCompanyId;
          if (!targetCompanyId) {
            targetCompanyId = this.toIntOrNull(this.communicationsSelectedCompanyId) || this.toIntOrNull(this.communicationsVisibleCompanies[0]?.id);
          }
          if (targetCompanyId) {
            await this.selectCommunicationsCompany(targetCompanyId, { composeMode });
          }
        },
        async openCommunicationsFromDealDocument(documentItem) {
          const documentId = this.toIntOrNull(documentItem?.id);
          const dealId = this.toIntOrNull(this.editingDealId);
          const companyId = this.toIntOrNull(this.forms.deals.companyId);
          if (!documentId || !dealId || !companyId) {
            this.setUiError("Не удалось определить счет или компанию для отправки.", { modal: true });
            return;
          }
          if (this.showModal) {
            this.closeModal();
          }
          await this.openCommunicationsSection({
            companyId,
            dealId,
            composeMode: "email",
            pendingDocument: {
              id: documentId,
              originalName: documentItem.originalName || "Документ",
              dealId,
              companyId,
            },
          });
        },
        openTelephonySettingsFromCommunications() {
          this.setSection("telephony");
        },
        async startCallFromCommunications() {
          const companyId = this.toIntOrNull(this.communicationsSelectedCompanyId);
          const phone = this.communicationsSelectedCompanyPhone;
          if (!companyId || !phone) {
            this.setUiError("У выбранной компании нет номера для звонка.", { modal: true });
            return;
          }
          await this.startNovofonCall({
            phone,
            entityType: "company",
            entityId: companyId,
            comment: `Звонок из раздела коммуникаций по компании ${this.selectedCommunicationsCompany?.name || ""}`.trim(),
          });
          await this.loadCommunicationsTimeline(companyId, { preserveSelection: true });
        },
        selectCommunicationsTimelineItem(itemKey) {
          this.communicationsSelectedTimelineItemKey = String(itemKey || "").trim();
          this.closeCommunicationsCompose();
        },
        resetCommunicationsSectionState() {
          this.communicationsSelectedCompanyId = null;
          this.communicationsContacts = [];
          this.communicationsConversations = [];
          this.communicationsMessages = [];
          this.communicationsCalls = [];
          this.communicationsTimelineFilter = "all";
          this.communicationsSelectedTimelineItemKey = "";
          this.closeCommunicationsCompose();
          this.clearCommunicationsPendingDocument();
        },
        mapDealDocumentDeliveryEvent(item) {
          const metadata = item && typeof item.metadata === "object" && !Array.isArray(item.metadata) ? item.metadata : {};
          return {
            id: this.toIntOrNull(item.id),
            eventType: String(item.event_type || "").trim(),
            eventTypeLabel: String(item.event_type_label || "").trim() || "Событие",
            happenedAt: String(item.happened_at || item.created_at || "").trim(),
            ipAddress: String(item.ip_address || "").trim(),
            userAgent: String(item.user_agent || "").trim(),
            metadata,
          };
        },
        mapDealDocumentDeliveryShare(item) {
          return {
            id: this.toIntOrNull(item.id),
            channel: String(item.channel || "").trim().toLowerCase(),
            recipient: String(item.recipient || "").trim(),
            messageStatus: String(item.message_status || "").trim().toLowerCase(),
            messageStatusLabel: this.communicationMessageStatusLabel(item.message_status),
            subject: String(item.subject || "").trim(),
            sentAt: String(item.sent_at || "").trim(),
            failedAt: String(item.failed_at || "").trim(),
            lastErrorMessage: String(item.last_error_message || "").trim(),
            publicUrl: String(item.public_url || "").trim(),
            downloadUrl: String(item.download_url || "").trim(),
            firstOpenedAt: String(item.first_opened_at || "").trim(),
            lastOpenedAt: String(item.last_opened_at || "").trim(),
            lastDownloadedAt: String(item.last_downloaded_at || "").trim(),
            openCount: Math.max(0, Number(item.open_count) || 0),
            downloadCount: Math.max(0, Number(item.download_count) || 0),
            firstOpenIp: String(item.first_open_ip || "").trim(),
            lastOpenIp: String(item.last_open_ip || "").trim(),
            firstOpenUserAgent: String(item.first_open_user_agent || "").trim(),
            lastOpenUserAgent: String(item.last_open_user_agent || "").trim(),
            events: Array.isArray(item.events) ? item.events.map((eventItem) => this.mapDealDocumentDeliveryEvent(eventItem)) : [],
            createdAt: String(item.created_at || "").trim(),
            updatedAt: String(item.updated_at || "").trim(),
          };
        },
        getActiveCompanyConversation() {
          const conversationId = this.toIntOrNull(this.activeCompanyConversationId);
          if (!conversationId) return null;
          return (this.companyCommunications || []).find((item) => String(item.id) === String(conversationId)) || null;
        },
        getActiveDealConversation() {
          const conversationId = this.toIntOrNull(this.activeDealConversationId);
          if (!conversationId) return null;
          return (this.dealCommunications || []).find((item) => String(item.id) === String(conversationId)) || null;
        },
        normalizeCommunicationRecipientKey(channelCode, rawValue) {
          const normalizedChannel = String(channelCode || "").trim().toLowerCase();
          const raw = String(rawValue || "").trim();
          if (!raw) return "";
          if (normalizedChannel === "email") {
            const emailValue = raw.startsWith("email:") ? raw.slice(6) : raw;
            const normalizedEmail = String(emailValue || "").trim().toLowerCase();
            return normalizedEmail.includes("@") ? normalizedEmail : "";
          }
          if (normalizedChannel === "telegram") {
            const telegramValue = raw.startsWith("telegram:") ? raw.slice(9) : raw;
            const normalizedTelegram = String(telegramValue || "").trim();
            return normalizedTelegram ? `telegram:${normalizedTelegram}` : "";
          }
          return raw;
        },
        deriveConversationRecipientFromMessages(conversation, messages = []) {
          const channelCode = String(conversation?.channel || "").trim().toLowerCase();
          const sortedMessages = [...(Array.isArray(messages) ? messages : [])].sort((left, right) => {
            const leftAt = this.parseTaskDueTimestamp(left?.receivedAt || left?.sentAt || left?.createdAt) || 0;
            const rightAt = this.parseTaskDueTimestamp(right?.receivedAt || right?.sentAt || right?.createdAt) || 0;
            return rightAt - leftAt;
          });
          if (channelCode === "email" || channelCode === "telegram") {
            const latestIncoming = sortedMessages.find((item) => String(item?.direction || "").trim().toLowerCase() === "incoming");
            const incomingRecipient = this.normalizeCommunicationRecipientKey(channelCode, latestIncoming?.externalSenderKey);
            if (incomingRecipient) {
              return incomingRecipient;
            }
          }
          return this.deriveCommunicationRecipient(channelCode, conversation?.contactId);
        },
        getDefaultCommunicationComposer(conversation, messages = []) {
          return {
            subject: conversation?.channel === "email" ? String(conversation?.subject || "").trim() : "",
            bodyText: "",
            recipient: this.deriveConversationRecipientFromMessages(conversation, messages),
          };
        },
        getAutomationMessageDraftById(messageDraftId) {
          const normalizedDraftId = this.toIntOrNull(messageDraftId);
          if (!normalizedDraftId) return null;
          return (this.datasets.automationMessageDrafts || []).find((item) => String(item.id) === String(normalizedDraftId)) || null;
        },
        deriveCommunicationRecipient(channelCode, contactId) {
          const normalizedChannel = String(channelCode || "").trim().toLowerCase();
          const normalizedContactId = this.toIntOrNull(contactId);
          const contact = (this.datasets.contacts || []).find((item) => String(item.id) === String(normalizedContactId || ""));
          if (!contact) return "";
          if (normalizedChannel === "telegram") {
            return contact.telegram ? `telegram:${String(contact.telegram).trim()}` : "";
          }
          if (normalizedChannel === "email") {
            return contact.email ? `email:${String(contact.email).trim()}` : "";
          }
          return "";
        },
        setTouchResultPrompt(text = "") {
          this.touchResultPromptVisible = !!String(text || "").trim();
          this.touchResultPromptText = String(text || "").trim();
        },
        focusTouchResultField() {
          this.$nextTick(() => {
            const field = document.getElementById("touch-result-option");
            if (field && typeof field.focus === "function") {
              field.focus();
            }
          });
        },
        getDefaultDealCommunicationStartForm() {
          return {
            channel: "email",
            contactId: this.toIntOrNull(this.dealSummaryContact?.id),
            recipient: "",
            subject: this.forms.deals.title ? `По сделке: ${this.forms.deals.title}` : "",
            bodyText: "",
          };
        },
        getDefaultDealDocumentSendComposer(conversation = null) {
          const documentName = this.documentDisplayName(this.dealDocumentSendTarget?.originalName || "", "");
          return {
            subject: documentName || String(conversation?.subject || "").trim() || (this.forms.deals.title ? `По сделке: ${this.forms.deals.title}` : ""),
            bodyText: documentName ? `Направляю ссылку на ${documentName}.` : "",
            recipient: this.deriveConversationRecipientFromMessages(conversation, this.dealDocumentSendMessages),
          };
        },
        getDefaultDealDocumentSendStartForm() {
          const documentName = this.documentDisplayName(this.dealDocumentSendTarget?.originalName || "", "");
          return {
            channel: "email",
            contactId: this.toIntOrNull(this.dealSummaryContact?.id),
            recipient: "",
            subject: documentName || (this.forms.deals.title ? `По сделке: ${this.forms.deals.title}` : ""),
            bodyText: documentName ? `Направляю ссылку на ${documentName}.` : "",
          };
        },
        syncDealDocumentSendStartRecipient() {
          const contactId = this.toIntOrNull(this.dealDocumentSendStartForm.contactId);
          const contact = (this.dealCommunicationContactOptions || []).find((item) => String(item.id) === String(contactId || ""));
          if (!contact) {
            this.dealDocumentSendStartForm.recipient = "";
            return;
          }
          this.dealDocumentSendStartForm.recipient = contact.email ? `email:${String(contact.email).trim()}` : "";
        },
        syncDealCommunicationStartRecipient() {
          const channel = String(this.dealCommunicationStartForm.channel || "email").trim().toLowerCase();
          const contactId = this.toIntOrNull(this.dealCommunicationStartForm.contactId);
          const contact = (this.dealCommunicationContactOptions || []).find((item) => String(item.id) === String(contactId || ""));
          if (!contact) {
            this.dealCommunicationStartForm.recipient = "";
            return;
          }
          if (channel === "telegram") {
            this.dealCommunicationStartForm.recipient = contact.telegram ? `telegram:${String(contact.telegram).trim()}` : "";
            return;
          }
          this.dealCommunicationStartForm.recipient = contact.email ? `email:${String(contact.email).trim()}` : "";
        },
        toggleDealCommunicationStartForm() {
          this.showDealCommunicationStartForm = !this.showDealCommunicationStartForm;
          if (this.showDealCommunicationStartForm) {
            this.dealCommunicationStartForm = this.getDefaultDealCommunicationStartForm();
            this.syncDealCommunicationStartRecipient();
          }
        },
        closeDealDocumentSendSidebar() {
          this.showDealDocumentSendSidebar = false;
          this.isDealDocumentSendSidebarPreparing = false;
          this.isDealDocumentSendLoading = false;
          this.isDealDocumentDeliveryHistoryLoading = false;
          this.isDealDocumentSendMessagesLoading = false;
          this.isDealDocumentSendSending = false;
          this.isDealDocumentSendStarting = false;
          this.dealDocumentSendTarget = null;
          this.dealDocumentSendConversations = [];
          this.dealDocumentDeliveryHistory = [];
          this.dealDocumentSendMessages = [];
          this.activeDealDocumentSendConversationId = null;
          this.showDealDocumentSendStartForm = false;
          this.dealDocumentSendComposer = {
            subject: "",
            bodyText: "",
            recipient: "",
          };
          this.dealDocumentSendStartForm = this.getDefaultDealDocumentSendStartForm();
        },
        async loadDealDocumentDeliveryHistory(documentId, options = {}) {
          const normalizedDocumentId = this.toIntOrNull(documentId);
          if (!normalizedDocumentId) {
            this.dealDocumentDeliveryHistory = [];
            return;
          }
          if (!options.silent) {
            this.isDealDocumentDeliveryHistoryLoading = true;
          }
          try {
            const payload = await this.apiRequest(`/api/v1/deal-documents/${normalizedDocumentId}/delivery-history/`);
            const records = Array.isArray(payload) ? payload : this.normalizePaginatedResponse(payload);
            this.dealDocumentDeliveryHistory = records.map((item) => this.mapDealDocumentDeliveryShare(item));
          } finally {
            this.isDealDocumentDeliveryHistoryLoading = false;
          }
        },
        async loadDealDocumentSendConversationMessages(conversationId, options = {}) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          if (!normalizedConversationId) {
            this.dealDocumentSendMessages = [];
            return;
          }
          if (!options.silent) {
            this.isDealDocumentSendMessagesLoading = true;
          }
          try {
            const payload = await this.apiRequest(`/api/v1/communications/conversations/${normalizedConversationId}/messages/`);
            const records = Array.isArray(payload) ? payload : this.normalizePaginatedResponse(payload);
            this.dealDocumentSendMessages = records.map((item) => this.mapCommunicationMessage(item));
            const conversation = this.activeDealDocumentSendConversation;
            if (conversation && String(conversation.id) === String(normalizedConversationId) && !String(this.dealDocumentSendComposer.bodyText || "").trim()) {
              this.dealDocumentSendComposer = this.getDefaultDealDocumentSendComposer(conversation);
            }
          } finally {
            this.isDealDocumentSendMessagesLoading = false;
          }
        },
        async selectDealDocumentSendConversation(conversationId, options = {}) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          this.activeDealDocumentSendConversationId = normalizedConversationId;
          this.showDealDocumentSendStartForm = false;
          const conversation = this.activeDealDocumentSendConversation;
          this.dealDocumentSendComposer = this.getDefaultDealDocumentSendComposer(conversation);
          if (normalizedConversationId) {
            await this.loadDealDocumentSendConversationMessages(normalizedConversationId, options);
          } else {
            this.dealDocumentSendMessages = [];
          }
        },
        async loadDealDocumentSendConversations(options = {}) {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) {
            this.dealDocumentSendConversations = [];
            this.dealDocumentSendMessages = [];
            this.activeDealDocumentSendConversationId = null;
            return;
          }
          const previousConversationId = this.toIntOrNull(this.activeDealDocumentSendConversationId);
          if (!options.silent) {
            this.isDealDocumentSendLoading = true;
          }
          try {
            const payload = await this.apiRequest(`/api/v1/communications/conversations/?deal=${dealId}&page_size=100`);
            const records = this.normalizePaginatedResponse(payload)
              .map((item) => this.mapConversation(item))
              .filter((item) => String(item.channel || "").trim().toLowerCase() === "email");
            this.dealDocumentSendConversations = records;
            let nextConversationId = options.preserveSelection ? previousConversationId : null;
            if (!nextConversationId || !records.some((item) => String(item.id) === String(nextConversationId))) {
              nextConversationId = records[0]?.id || null;
            }
            const shouldReloadMessages = !!nextConversationId && (
              options.forceReloadMessages
              || String(nextConversationId) !== String(previousConversationId || "")
              || !this.dealDocumentSendMessages.length
            );
            this.activeDealDocumentSendConversationId = nextConversationId;
            this.dealDocumentSendComposer = this.getDefaultDealDocumentSendComposer(this.activeDealDocumentSendConversation);
            if (shouldReloadMessages) {
              await this.loadDealDocumentSendConversationMessages(nextConversationId, { silent: options.silent });
            } else if (!nextConversationId) {
              this.dealDocumentSendMessages = [];
            }
          } finally {
            this.isDealDocumentSendLoading = false;
          }
        },
        async openDealDocumentSendSidebar(documentItem) {
          const documentId = this.toIntOrNull(documentItem?.id);
          if (!documentId || !this.toIntOrNull(this.editingDealId) || this.isDealDocumentSendSidebarPreparing) {
            return;
          }
          this.clearUiErrors({ modalOnly: true });
          this.isDealDocumentSendSidebarPreparing = true;
          try {
            this.dealDocumentSendTarget = {
              id: documentId,
              originalName: documentItem.originalName || "Документ",
              fileUrl: documentItem.fileUrl || "",
            };
            await Promise.all([
              this.loadContactsForSelectedDealCompany(),
              this.loadDealDocumentSendConversations({ preserveSelection: false, forceReloadMessages: true }),
              this.loadDealDocumentDeliveryHistory(documentId, { silent: true }),
            ]);
            this.dealDocumentSendStartForm = this.getDefaultDealDocumentSendStartForm();
            this.syncDealDocumentSendStartRecipient();
            this.showDealDocumentSendStartForm = !this.dealDocumentSendEmailConversations.length;
            this.showDealDocumentSendSidebar = true;
          } catch (error) {
            this.setUiError(`Ошибка подготовки отправки документа: ${error.message}`, { modal: true });
            this.closeDealDocumentSendSidebar();
          } finally {
            this.isDealDocumentSendSidebarPreparing = false;
          }
        },
        resetCompanyCommunicationsState() {
          this.showCompanyCommunicationsPanel = false;
          this.isCompanyCommunicationsLoading = false;
          this.isCompanyConversationMessagesLoading = false;
          this.isCompanyCommunicationSending = false;
          this.activeAutomationMessageDraftPreview = null;
          this.companyCommunications = [];
          this.companyConversationMessages = [];
          this.activeCompanyConversationId = null;
          this.companyCommunicationComposer = this.getDefaultCommunicationComposer(null);
          this.stopCommunicationsPollingIfIdle();
        },
        resetDealCommunicationsState() {
          this.showDealCommunicationsPanel = false;
          this.isDealCommunicationsLoading = false;
          this.isDealConversationMessagesLoading = false;
          this.isDealCommunicationSending = false;
          this.isDealCommunicationStarting = false;
          this.dealCommunications = [];
          this.dealManualBindingConversations = [];
          this.dealConversationMessages = [];
          this.activeDealConversationId = null;
          this.activeAutomationMessageDraftPreview = null;
          this.showDealCommunicationStartForm = false;
          this.dealCommunicationComposer = this.getDefaultCommunicationComposer(null);
          this.dealCommunicationStartForm = this.getDefaultDealCommunicationStartForm();
          this.stopCommunicationsPollingIfIdle();
        },
        ensureCommunicationsPolling() {
          if (this.communicationsPollTimer || typeof window === "undefined") return;
          this.communicationsPollTimer = window.setInterval(() => {
            this.pollOpenCommunicationsPanels().catch(() => {});
          }, 30000);
        },
        ensureAutomationNotificationsPolling() {
          if (this.automationNotificationsPollTimer || typeof window === "undefined") return;
          this.automationNotificationsPollTimer = window.setInterval(() => {
            this.pollAutomationNotifications().catch(() => {});
          }, 30000);
        },
        sectionUsesAutomationData(section) {
          return ["deals", "tasks", "touches"].includes(String(section || "").trim());
        },
        async ensureAutomationDataLoaded(force = false) {
          if (!force && this.automationDataLoaded) {
            return;
          }
          if (this.automationDataLoadPromise) {
            return this.automationDataLoadPromise;
          }
          this.automationDataLoadPromise = Promise.all([
            this.loadAutomationDrafts(),
            this.loadAutomationQueue(),
            this.loadAutomationMessageDrafts(),
          ]).then(() => {
            this.automationDataLoaded = true;
          }).finally(() => {
            this.automationDataLoadPromise = null;
          });
          return this.automationDataLoadPromise;
        },
        stopAutomationNotificationsPolling() {
          if (this.automationNotificationsPollTimer && typeof window !== "undefined") {
            window.clearInterval(this.automationNotificationsPollTimer);
          }
          this.automationNotificationsPollTimer = null;
          this.isAutomationNotificationsPolling = false;
        },
        stopCommunicationsPollingIfIdle() {
          if (
            this.showModal
            && (this.showCompanyCommunicationsPanel || this.showDealCommunicationsPanel)
          ) {
            return;
          }
          if (this.communicationsPollTimer && typeof window !== "undefined") {
            window.clearInterval(this.communicationsPollTimer);
          }
          this.communicationsPollTimer = null;
        },
        async pollOpenCommunicationsPanels() {
          if (!this.showModal) {
            this.stopCommunicationsPollingIfIdle();
            return;
          }
          const tasks = [];
          if (this.showCompanyCommunicationsPanel && this.editingCompanyId) {
            tasks.push(this.loadCompanyCommunications({
              silent: true,
              preserveSelection: true,
              forceReloadMessages: true,
            }));
          }
          if (this.showDealCommunicationsPanel && this.editingDealId) {
            tasks.push(this.loadDealCommunications({
              silent: true,
              preserveSelection: true,
              forceReloadMessages: true,
            }));
          }
          if (this.showDealDocumentSendSidebar && this.toIntOrNull(this.dealDocumentSendTarget?.id)) {
            tasks.push(this.loadDealDocumentDeliveryHistory(this.toIntOrNull(this.dealDocumentSendTarget?.id), { silent: true }));
          }
          if (!tasks.length) {
            this.stopCommunicationsPollingIfIdle();
            return;
          }
          await Promise.all(tasks);
        },
        async pollAutomationNotifications() {
          if (this.isAutomationNotificationsPolling) return;
          if (typeof document !== "undefined" && document.hidden) return;
          if (!this.automationDataLoaded) return;
          this.isAutomationNotificationsPolling = true;
          try {
            await this.ensureAutomationDataLoaded(true);
          } finally {
            this.isAutomationNotificationsPolling = false;
          }
        },
        async loadCompanyConversationMessages(conversationId, options = {}) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          if (!normalizedConversationId) {
            this.companyConversationMessages = [];
            return;
          }
          if (!options.silent) {
            this.isCompanyConversationMessagesLoading = true;
          }
          try {
            const payload = await this.apiRequest(`/api/v1/communications/conversations/${normalizedConversationId}/messages/`);
            const records = Array.isArray(payload) ? payload : this.normalizePaginatedResponse(payload);
            this.companyConversationMessages = records.map((item) => this.mapCommunicationMessage(item));
            const conversation = this.getActiveCompanyConversation();
            if (conversation && String(conversation.id) === String(normalizedConversationId) && !String(this.companyCommunicationComposer.bodyText || "").trim()) {
              this.companyCommunicationComposer = this.getDefaultCommunicationComposer(conversation, this.companyConversationMessages);
            }
          } finally {
            this.isCompanyConversationMessagesLoading = false;
          }
        },
        async loadDealConversationMessages(conversationId, options = {}) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          if (!normalizedConversationId) {
            this.dealConversationMessages = [];
            return;
          }
          if (!options.silent) {
            this.isDealConversationMessagesLoading = true;
          }
          try {
            const payload = await this.apiRequest(`/api/v1/communications/conversations/${normalizedConversationId}/messages/`);
            const records = Array.isArray(payload) ? payload : this.normalizePaginatedResponse(payload);
            this.dealConversationMessages = records.map((item) => this.mapCommunicationMessage(item));
            const conversation = this.getActiveDealConversation();
            if (conversation && String(conversation.id) === String(normalizedConversationId) && !String(this.dealCommunicationComposer.bodyText || "").trim()) {
              this.dealCommunicationComposer = this.getDefaultCommunicationComposer(conversation, this.dealConversationMessages);
            }
          } finally {
            this.isDealConversationMessagesLoading = false;
          }
        },
        async selectCompanyConversation(conversationId, options = {}) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          this.activeCompanyConversationId = normalizedConversationId;
          this.activeAutomationMessageDraftPreview = null;
          const conversation = this.getActiveCompanyConversation();
          this.companyCommunicationComposer = this.getDefaultCommunicationComposer(conversation);
          if (normalizedConversationId) {
            await this.loadCompanyConversationMessages(normalizedConversationId, options);
          } else {
            this.companyConversationMessages = [];
          }
        },
        async selectDealConversation(conversationId, options = {}) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          this.activeDealConversationId = normalizedConversationId;
          this.activeAutomationMessageDraftPreview = null;
          const conversation = this.getActiveDealConversation();
          this.dealCommunicationComposer = this.getDefaultCommunicationComposer(conversation);
          if (normalizedConversationId) {
            await this.loadDealConversationMessages(normalizedConversationId, options);
          } else {
            this.dealConversationMessages = [];
          }
        },
        async loadCompanyCommunications(options = {}) {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) {
            this.companyCommunications = [];
            this.companyConversationMessages = [];
            this.activeCompanyConversationId = null;
            return;
          }
          const previousConversationId = this.toIntOrNull(this.activeCompanyConversationId);
          if (!options.silent) {
            this.isCompanyCommunicationsLoading = true;
          }
          try {
            const payload = await this.apiRequest(`/api/v1/communications/conversations/?client=${companyId}&page_size=100`);
            const records = this.normalizePaginatedResponse(payload).map((item) => this.mapConversation(item));
            this.companyCommunications = records;
            let nextConversationId = options.preserveSelection ? previousConversationId : null;
            if (!nextConversationId || !records.some((item) => String(item.id) === String(nextConversationId))) {
              nextConversationId = records[0]?.id || null;
            }
            const shouldReloadMessages = !!nextConversationId && (
              options.forceReloadMessages
              || String(nextConversationId) !== String(previousConversationId || "")
              || !this.companyConversationMessages.length
            );
            this.activeCompanyConversationId = nextConversationId;
            this.companyCommunicationComposer = this.getDefaultCommunicationComposer(this.getActiveCompanyConversation());
            if (shouldReloadMessages) {
              await this.loadCompanyConversationMessages(nextConversationId, { silent: options.silent });
            } else if (!nextConversationId) {
              this.companyConversationMessages = [];
            }
            if (this.showCompanyCommunicationsPanel) {
              this.ensureCommunicationsPolling();
            }
          } finally {
            this.isCompanyCommunicationsLoading = false;
          }
        },
        async loadDealCommunications(options = {}) {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) {
            this.dealCommunications = [];
            this.dealManualBindingConversations = [];
            this.dealConversationMessages = [];
            this.activeDealConversationId = null;
            return;
          }
          const companyId = this.toIntOrNull(this.forms.deals.companyId);
          const previousConversationId = this.toIntOrNull(this.activeDealConversationId);
          if (!options.silent) {
            this.isDealCommunicationsLoading = true;
          }
          try {
            const requests = [
              this.apiRequest(`/api/v1/communications/conversations/?deal=${dealId}&page_size=100`)
            ];
            if (companyId) {
              requests.push(this.apiRequest(`/api/v1/communications/conversations/?client=${companyId}&requires_manual_binding=true&page_size=100`));
            } else {
              requests.push(Promise.resolve([]));
            }
            const [dealPayload, manualPayload] = await Promise.all(requests);
            const dealRecords = this.normalizePaginatedResponse(dealPayload).map((item) => this.mapConversation(item));
            const manualRecords = this.normalizePaginatedResponse(manualPayload)
              .map((item) => this.mapConversation(item))
              .filter((item) => item.requiresManualBinding && !this.toIntOrNull(item.dealId));
            this.dealCommunications = dealRecords;
            this.dealManualBindingConversations = manualRecords;
            let nextConversationId = options.preserveSelection ? previousConversationId : null;
            if (!nextConversationId || !dealRecords.some((item) => String(item.id) === String(nextConversationId))) {
              nextConversationId = dealRecords[0]?.id || null;
            }
            const shouldReloadMessages = !!nextConversationId && (
              options.forceReloadMessages
              || String(nextConversationId) !== String(previousConversationId || "")
              || !this.dealConversationMessages.length
            );
            this.activeDealConversationId = nextConversationId;
            this.dealCommunicationComposer = this.getDefaultCommunicationComposer(this.getActiveDealConversation());
            if (shouldReloadMessages) {
              await this.loadDealConversationMessages(nextConversationId, { silent: options.silent });
            } else if (!nextConversationId) {
              this.dealConversationMessages = [];
            }
            if (this.showDealCommunicationsPanel) {
              this.ensureCommunicationsPolling();
            }
          } finally {
            this.isDealCommunicationsLoading = false;
          }
        },
        async bindCompanyConversation(conversationId) {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          const normalizedConversationId = this.toIntOrNull(conversationId);
          if (!companyId || !normalizedConversationId) return;
          await this.apiRequest(`/api/v1/communications/conversations/${normalizedConversationId}/bind/`, {
            method: "POST",
            body: {
              client: companyId,
            }
          });
          await this.loadCompanyCommunications({ preserveSelection: true, forceReloadMessages: true });
        },
        async bindDealConversationToCurrentDeal(conversationId) {
          const dealId = this.toIntOrNull(this.editingDealId);
          const companyId = this.toIntOrNull(this.forms.deals.companyId);
          const normalizedConversationId = this.toIntOrNull(conversationId);
          if (!dealId || !normalizedConversationId) return;
          await this.apiRequest(`/api/v1/communications/conversations/${normalizedConversationId}/bind/`, {
            method: "POST",
            body: {
              client: companyId,
              deal: dealId,
            }
          });
          this.activeDealConversationId = normalizedConversationId;
          await this.loadDealCommunications({ preserveSelection: true, forceReloadMessages: true });
          if (companyId && this.showCompanyCommunicationsPanel && this.toIntOrNull(this.editingCompanyId) === companyId) {
            await this.loadCompanyCommunications({ silent: true, preserveSelection: true, forceReloadMessages: true });
          }
        },
        extractOutgoingMessageResponse(response) {
          if (response && typeof response === "object" && response.message && typeof response.message === "object") {
            return response.message;
          }
          return response;
        },
        ensureOutgoingMessageDelivered(response, contextLabel = "Сообщение") {
          const message = this.extractOutgoingMessageResponse(response);
          const status = String(message?.status || "").trim();
          const errorText = String(message?.last_error_message || "").trim();
          if (status === "sent") {
            return message;
          }
          if (status === "requires_manual_retry") {
            throw new Error(errorText || `${contextLabel} не отправлено автоматически и требует ручной отправки.`);
          }
          if (status === "failed") {
            throw new Error(errorText || `${contextLabel} не отправлено.`);
          }
          if (status === "queued" || status === "sending") {
            throw new Error(`${contextLabel} поставлено в очередь, но отправка ещё не подтверждена.`);
          }
          throw new Error(`${contextLabel} не отправлено. Текущий статус: ${status || "неизвестен"}.`);
        },
        ensureDocumentRecipientFilled(rawRecipient) {
          const recipient = String(rawRecipient || "").trim();
          if (!recipient) {
            throw new Error("Укажите получателя письма.");
          }
          return recipient;
        },
        async sendCompanyCommunicationMessage() {
          const conversation = this.getActiveCompanyConversation();
          if (!conversation?.id || this.isCompanyCommunicationSending) return;
          this.clearUiErrors({ modalOnly: true });
          this.isCompanyCommunicationSending = true;
          try {
            const response = await this.apiRequest(`/api/v1/communications/conversations/${conversation.id}/send/`, {
              method: "POST",
              body: {
                subject: this.companyCommunicationComposer.subject,
                body_text: this.companyCommunicationComposer.bodyText,
                recipient: this.companyCommunicationComposer.recipient,
              }
            });
            this.ensureOutgoingMessageDelivered(response, "Письмо");
            this.companyCommunicationComposer = this.getDefaultCommunicationComposer(conversation);
            await this.loadCompanyCommunications({ preserveSelection: true, forceReloadMessages: true });
          } catch (error) {
            this.setUiError(`Ошибка отправки сообщения: ${error.message}`, { modal: true });
          } finally {
            this.isCompanyCommunicationSending = false;
          }
        },
        async sendDealCommunicationMessage() {
          const conversation = this.getActiveDealConversation();
          if (!conversation?.id || this.isDealCommunicationSending) return;
          this.clearUiErrors({ modalOnly: true });
          this.isDealCommunicationSending = true;
          try {
            const response = await this.apiRequest(`/api/v1/communications/conversations/${conversation.id}/send/`, {
              method: "POST",
              body: {
                subject: this.dealCommunicationComposer.subject,
                body_text: this.dealCommunicationComposer.bodyText,
                recipient: this.dealCommunicationComposer.recipient,
              }
            });
            this.ensureOutgoingMessageDelivered(response, "Письмо");
            this.dealCommunicationComposer = this.getDefaultCommunicationComposer(conversation);
            await this.loadDealCommunications({ preserveSelection: true, forceReloadMessages: true });
          } catch (error) {
            this.setUiError(`Ошибка отправки сообщения: ${error.message}`, { modal: true });
          } finally {
            this.isDealCommunicationSending = false;
          }
        },
        async refreshAfterDealDocumentSend() {
          const tasks = [
            this.loadSection("touches"),
            this.loadSection("deals"),
            this.loadAutomationDrafts(),
            this.loadAutomationQueue(),
            this.loadAutomationMessageDrafts(),
          ];
          if (this.showDealCommunicationsPanel && this.toIntOrNull(this.editingDealId)) {
            tasks.push(this.loadDealCommunications({ preserveSelection: true, forceReloadMessages: true, silent: true }));
          }
          const companyId = this.toIntOrNull(this.forms.deals.companyId);
          if (this.showCompanyCommunicationsPanel && companyId && this.toIntOrNull(this.editingCompanyId) === companyId) {
            tasks.push(this.loadCompanyCommunications({ preserveSelection: true, forceReloadMessages: true, silent: true }));
          }
          await Promise.all(tasks);
        },
        async sendDealDocumentCommunicationMessage() {
          const conversation = this.activeDealDocumentSendConversation;
          const documentId = this.toIntOrNull(this.dealDocumentSendTarget?.id);
          if (!conversation?.id || !documentId || this.isDealDocumentSendSending) return;
          this.clearUiErrors({ modalOnly: true });
          this.isDealDocumentSendSending = true;
          try {
            const recipient = this.ensureDocumentRecipientFilled(this.dealDocumentSendComposer.recipient);
            const response = await this.apiRequest(`/api/v1/communications/conversations/${conversation.id}/send/`, {
              method: "POST",
              body: {
                subject: this.dealDocumentSendComposer.subject,
                body_text: this.dealDocumentSendComposer.bodyText,
                recipient,
                deal_document: documentId,
                touch_result_code: "proposal_sent",
                touch_summary: `Отправлен документ: ${this.dealDocumentSendTarget.originalName || "Документ"}`,
              }
            });
            let deliveryError = null;
            try {
              this.ensureOutgoingMessageDelivered(response, "Письмо");
            } catch (error) {
              deliveryError = error;
            }
            await Promise.all([
              this.loadDealDocumentSendConversations({ preserveSelection: true, forceReloadMessages: true, silent: true }),
              this.loadDealDocumentDeliveryHistory(documentId, { silent: true }),
              this.refreshAfterDealDocumentSend(),
            ]);
            if (deliveryError) {
              throw deliveryError;
            }
          } catch (error) {
            this.setUiError(`Ошибка отправки документа: ${error.message}`, { modal: true });
          } finally {
            this.isDealDocumentSendSending = false;
          }
        },
        async startDealDocumentCommunicationConversation() {
          const documentId = this.toIntOrNull(this.dealDocumentSendTarget?.id);
          if (!documentId || this.isDealDocumentSendStarting || !this.toIntOrNull(this.editingDealId)) return;
          this.clearUiErrors({ modalOnly: true });
          this.isDealDocumentSendStarting = true;
          try {
            const recipient = this.ensureDocumentRecipientFilled(this.dealDocumentSendStartForm.recipient);
            const response = await this.apiRequest("/api/v1/communications/conversations/start/", {
              method: "POST",
              body: {
                channel: "email",
                deal: this.toIntOrNull(this.editingDealId),
                client: this.toIntOrNull(this.forms.deals.companyId),
                contact: this.toIntOrNull(this.dealDocumentSendStartForm.contactId),
                recipient,
                subject: this.dealDocumentSendStartForm.subject,
                body_text: this.dealDocumentSendStartForm.bodyText,
                deal_document: documentId,
                touch_result_code: "proposal_sent",
                touch_summary: `Отправлен документ: ${this.dealDocumentSendTarget.originalName || "Документ"}`,
              }
            });
            let deliveryError = null;
            try {
              this.ensureOutgoingMessageDelivered(response, "Письмо");
            } catch (error) {
              deliveryError = error;
            }
            const createdConversationId = this.toIntOrNull(response?.conversation?.id);
            await Promise.all([
              this.loadDealDocumentSendConversations({ preserveSelection: false, forceReloadMessages: true, silent: true }),
              this.loadDealDocumentDeliveryHistory(documentId, { silent: true }),
              this.refreshAfterDealDocumentSend(),
            ]);
            this.showDealDocumentSendStartForm = false;
            if (createdConversationId) {
              await this.selectDealDocumentSendConversation(createdConversationId, { silent: true });
            }
            if (deliveryError) {
              throw deliveryError;
            }
          } catch (error) {
            this.setUiError(`Ошибка создания диалога для отправки документа: ${error.message}`, { modal: true });
          } finally {
            this.isDealDocumentSendStarting = false;
          }
        },
        async startDealCommunicationConversation() {
          if (this.isDealCommunicationStarting || !this.toIntOrNull(this.editingDealId)) return;
          this.clearUiErrors({ modalOnly: true });
          this.isDealCommunicationStarting = true;
          try {
            const response = await this.apiRequest("/api/v1/communications/conversations/start/", {
              method: "POST",
              body: {
                channel: this.dealCommunicationStartForm.channel,
                deal: this.toIntOrNull(this.editingDealId),
                client: this.toIntOrNull(this.forms.deals.companyId),
                contact: this.toIntOrNull(this.dealCommunicationStartForm.contactId),
                recipient: this.dealCommunicationStartForm.recipient,
                subject: this.dealCommunicationStartForm.subject,
                body_text: this.dealCommunicationStartForm.bodyText,
              }
            });
            this.ensureOutgoingMessageDelivered(response, "Письмо");
            const createdConversationId = this.toIntOrNull(response?.conversation?.id);
            this.showDealCommunicationStartForm = false;
            this.dealCommunicationStartForm = this.getDefaultDealCommunicationStartForm();
            await this.loadDealCommunications({ preserveSelection: false, forceReloadMessages: true });
            if (createdConversationId) {
              await this.selectDealConversation(createdConversationId, { silent: true });
            }
          } catch (error) {
            this.setUiError(`Ошибка старта переписки: ${error.message}`, { modal: true });
          } finally {
            this.isDealCommunicationStarting = false;
          }
        },
        async quickOpenDealCommunications() {
          await this.toggleDealCommunicationsPanel();
        },
        toggleCompanyNoteDraft() {
          this.showCompanyNoteDraft = !this.showCompanyNoteDraft;
          if (!this.showCompanyNoteDraft) {
            this.forms.companies.noteDraft = "";
          }
        },
        async apiRequest(url, options = {}) {
          const headers = { ...(options.headers || {}) };
          const method = String(options.method || "GET").toUpperCase();
          const hasBody = options.body !== undefined;
          const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
          const requiresCsrf = ["POST", "PUT", "PATCH", "DELETE"].includes(method);
          if (requiresCsrf) {
            headers["X-CSRFToken"] = this.getCsrfToken();
          }
          if (hasBody) {
            if (!isFormData) {
              headers["Content-Type"] = "application/json";
            }
          }
          const response = await fetch(url, {
            method,
            credentials: "same-origin",
            headers,
            body: hasBody ? (isFormData ? options.body : JSON.stringify(options.body)) : undefined
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
        normalizeTouchChannelCode(channelOrName) {
          const raw = typeof channelOrName === "string"
            ? channelOrName
            : (channelOrName?.code || channelOrName?.name || "");
          const normalized = String(raw || "").trim().toLowerCase();
          const aliases = {
            "телефон": "call",
            "звонок": "call",
            "call": "call",
            "email": "email",
            "e-mail": "email",
            "почта": "email",
            "whatsapp": "whatsapp",
            "ватсап": "whatsapp",
            "telegram": "telegram",
            "телеграм": "telegram",
            "meeting": "meeting",
            "встреча": "meeting",
            "proposal": "proposal",
            "предложение": "proposal",
            "коммерческое предложение": "proposal",
            "кп": "proposal",
            "document": "documents",
            "documents": "documents",
            "документ": "documents",
            "документы": "documents",
            "файлы": "documents",
          };
          if (aliases[normalized]) {
            return aliases[normalized];
          }
          return normalized
            .replace(/\s+/g, "_")
            .replace(/[^a-zа-я0-9_]/gi, "");
        },
        resolveTouchEventTypeFromParts(channelLike, directionValue, resultCodeValue = "") {
          const channelCode = this.normalizeTouchChannelCode(channelLike);
          const resultCode = String(resultCodeValue || "").trim().toLowerCase();
          const direction = String(directionValue || "").trim().toLowerCase();
          const directEventTypesByResultCode = {
            meeting_scheduled: "meeting_scheduled",
            meeting_rescheduled: "meeting_rescheduled",
            meeting_cancelled: "meeting_cancelled",
            meeting_completed: "meeting_completed",
            meeting_no_show: "meeting_no_show",
            proposal_requested: "proposal_sent",
            proposal_sent: "proposal_sent",
            proposal_received: "proposal_received_by_client",
            proposal_under_review: "proposal_received_by_client",
            proposal_revision_requested: "proposal_revision_requested",
            discount_requested: "proposal_revision_requested",
            documents_requested: "documents_requested",
            contract_sent: "contract_sent",
            contract_under_review: "contract_under_review",
            contract_revision_requested: "contract_revision_requested",
            contract_agreed: "contract_agreed",
            invoice_sent: "invoice_sent",
            invoice_accepted: "invoice_received_by_client",
            waiting_payment: "payment_waiting",
            payment_confirmed: "payment_confirmed",
          };
          if (!channelCode) return "";
          if (channelCode === "call" && resultCode === "no_answer") {
            return "call_no_answer";
          }
          if (directEventTypesByResultCode[resultCode]) {
            return directEventTypesByResultCode[resultCode];
          }
          if (channelCode === "call") {
            return "call_completed";
          }
          if (channelCode === "meeting") {
            return "meeting_completed";
          }
          if (channelCode === "email") {
            return `email_${direction === "incoming" ? "received" : "sent"}`;
          }
          if (channelCode === "telegram") {
            return `telegram_message_${direction === "incoming" ? "received" : "sent"}`;
          }
          if (channelCode === "whatsapp") {
            return `whatsapp_message_${direction === "incoming" ? "received" : "sent"}`;
          }
          if (["documents", "proposal"].includes(channelCode)) {
            return `${channelCode}_${direction === "incoming" ? "received" : "sent"}`;
          }
          return `${channelCode}_${direction || "outgoing"}`;
        },
        resolveTouchEventTypeFromItem(touch) {
          if (!touch || typeof touch !== "object") return "";
          return this.resolveTouchEventTypeFromParts(
            { code: touch.channelCode, name: touch.channelName },
            touch.direction,
            touch.resultOptionCode
          );
        },
        applyTouchAutomationRule() {
          const matchedRule = this.matchedTouchAutomationRule;
          if (!matchedRule) {
            return;
          }

          const matchedOutcome = this.matchedTouchAutomationOutcome;
          if (!this.toIntOrNull(this.forms.touches.resultOptionId) && matchedOutcome?.id) {
            this.forms.touches.resultOptionId = matchedOutcome.id;
          }

          const matchedTemplate = this.matchedTouchAutomationNextStepTemplate;
          if (!String(this.forms.touches.nextStep || "").trim() && matchedTemplate?.name) {
            this.forms.touches.nextStep = matchedTemplate.name;
          }
        },
        touchAutomationModeLabel(value) {
          const normalized = String(value || "").trim();
          if (normalized === "draft") return "Черновик касания";
          if (normalized === "create") return "Создать касание";
          return "Без автокасания";
        },
        automationPriorityRank(priority) {
          const normalized = String(priority || "").trim();
          const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
          return priorityOrder[normalized] ?? 99;
        },
        findAutomationRuleByEventType(eventType) {
          const normalized = String(eventType || "").trim();
          if (!normalized) return null;
          return (this.metaOptions.automationRules || []).find((item) => (
            !!item.is_active && String(item.event_type || "").trim() === normalized
          )) || null;
        },
        automationEventLabel(touch) {
          if (!touch || typeof touch !== "object") return "Событие";
          const channelName = String(touch.channelName || "").trim();
          const direction = String(touch.direction || "").trim();
          if (channelName) {
            if (direction === "incoming") return `Входящее ${channelName}`;
            if (direction === "outgoing") return `Исходящее ${channelName}`;
            return channelName;
          }
          return touch.resultOptionName || touch.summary || "Событие";
        },
        buildAutomationTouchEntry(touch) {
          if (!touch || typeof touch !== "object") return null;
          const eventType = this.resolveTouchEventTypeFromItem(touch);
          const rule = this.findAutomationRuleByEventType(eventType);
          if (!rule) return null;
          const uiMode = String(rule.ui_mode || "history_only").trim();
          const uiPriority = String(rule.ui_priority || "low").trim();
          const suggestedNextStep = String(
            rule.next_step_template_name
            || touch.nextStep
            || ""
          ).trim();
          return {
            id: `deal-automation-touch-${touch.id}`,
            touch,
            touchId: this.toIntOrNull(touch.id),
            eventType,
            eventLabel: this.automationEventLabel(touch),
            title: touch.summary || touch.resultOptionName || this.automationEventLabel(touch),
            summary: String(touch.summary || "").trim(),
            resultName: String(touch.resultOptionName || "").trim(),
            happenedAtRaw: touch.happenedAtRaw || null,
            nextStepAtRaw: touch.nextStepAtRaw || null,
            ownerName: String(touch.ownerName || "").trim(),
            uiMode,
            uiPriority,
            priorityRank: this.automationPriorityRank(uiPriority),
            rule,
            recommendedAction: String(rule.next_step_template_name || "").trim(),
            suggestedNextStep,
            suggestedNextStepAt: touch.nextStepAtRaw || null,
            defaultTaskCategoryId: this.findPreferredTaskCategoryId({
              usesCommunicationChannel: !!touch.channelId,
              requiresFollowUp: !touch.channelId,
              satisfiesDealNextStepRequirement: !!touch.channelId,
            }),
            defaultCommunicationChannelId: touch.channelId || null,
            needsAttention: (
              uiMode === "needs_attention"
              || !!rule.show_in_attention_queue
              || !!rule.require_manager_confirmation
            ),
            isSignal: uiMode === "signal",
            isDraft: (
              uiMode === "draft_touch"
              || String(rule.create_touchpoint_mode || "").trim() === "draft"
            ),
            isSignificant: (
              this.automationPriorityRank(uiPriority) <= this.automationPriorityRank("high")
              || ["needs_attention", "next_step_prompt", "draft_touch"].includes(uiMode)
              || ["call", "meeting"].includes(this.normalizeTouchChannelCode({ code: touch.channelCode, name: touch.channelName }))
              || String(touch.direction || "").trim() === "incoming"
            ),
            hasSuggestedNextStep: !!suggestedNextStep,
          };
        },
        buildAutomationDraftEntry(draft) {
          if (!draft || typeof draft !== "object") return null;
          const uiPriority = String(draft.automationRuleUiPriority || "medium").trim();
          const rule = (this.metaOptions.automationRules || []).find(
            (item) => String(item.id) === String(draft.automationRuleId || "")
          ) || null;
          const eventLabel = this.automationChainLabel({
            rule: { merge_key: rule?.merge_key || "" },
            eventLabel: draft.title || draft.sourceEventType || "Черновик",
          });
          return {
            id: `automation-draft-${draft.id}`,
            draftId: this.toIntOrNull(draft.id),
            draftKind: String(draft.draftKind || "").trim(),
            touchId: this.toIntOrNull(draft.sourceTouchId),
            eventType: String(draft.sourceEventType || "").trim(),
            eventLabel,
            title: draft.title || draft.summary || eventLabel,
            summary: String(draft.summary || "").trim(),
            resultName: String(draft.touchResultName || draft.outcomeName || "").trim(),
            happenedAtRaw: draft.sourceTouchHappenedAt || draft.createdAt || null,
            ownerName: String(draft.ownerName || "").trim(),
            uiPriority,
            priorityRank: this.automationPriorityRank(uiPriority),
            rule,
            suggestedNextStep: String(draft.proposedNextStep || "").trim(),
            suggestedNextStepAt: draft.proposedNextStepAt || null,
            defaultTaskCategoryId: this.findPreferredTaskCategoryId({
              usesCommunicationChannel: !!draft.proposedChannelId,
              requiresFollowUp: !draft.proposedChannelId,
              satisfiesDealNextStepRequirement: !!draft.proposedChannelId,
            }),
            defaultCommunicationChannelId: this.toIntOrNull(draft.proposedChannelId),
            recommendedAction: String(draft.proposedNextStep || "").trim(),
            hasSuggestedNextStep: !!String(draft.proposedNextStep || "").trim(),
            needsAttention: true,
            isDraft: true,
          };
        },
        buildAutomationQueueEntry(item) {
          if (!item || typeof item !== "object") return null;
          const uiPriority = String(item.automationRuleUiPriority || "medium").trim();
          const rule = (this.metaOptions.automationRules || []).find(
            (entry) => String(entry.id) === String(item.automationRuleId || "")
          ) || null;
          const eventLabel = this.automationChainLabel({
            rule: { merge_key: rule?.merge_key || "" },
            eventLabel: item.title || item.sourceEventType || "Событие",
          });
          return {
            id: `automation-queue-${item.id}`,
            queueId: this.toIntOrNull(item.id),
            queueKind: String(item.itemKind || "").trim(),
            touchId: this.toIntOrNull(item.sourceTouchId),
            ownerId: this.toIntOrNull(item.ownerId),
            leadId: this.toIntOrNull(item.leadId),
            dealId: this.toIntOrNull(item.dealId),
            clientId: this.toIntOrNull(item.clientId),
            contactId: this.toIntOrNull(item.contactId),
            eventType: String(item.sourceEventType || "").trim(),
            eventLabel,
            title: item.title || item.summary || eventLabel,
            summary: String(item.summary || "").trim(),
            resultName: String(item.touchResultName || item.outcomeName || "").trim(),
            happenedAtRaw: item.sourceTouchHappenedAt || item.createdAt || null,
            ownerName: String(item.ownerName || "").trim(),
            uiPriority,
            priorityRank: this.automationPriorityRank(uiPriority),
            rule,
            recommendedAction: String(item.recommendedAction || "").trim(),
            suggestedNextStep: String(item.proposedNextStep || item.recommendedAction || "").trim(),
            suggestedNextStepAt: item.proposedNextStepAt || null,
            defaultTaskCategoryId: this.findPreferredTaskCategoryId({
              usesCommunicationChannel: !!item.proposedChannelId,
              requiresFollowUp: !item.proposedChannelId,
              satisfiesDealNextStepRequirement: !!item.proposedChannelId,
            }),
            defaultCommunicationChannelId: this.toIntOrNull(item.proposedChannelId),
            hasSuggestedNextStep: !!String(item.proposedNextStep || item.recommendedAction || "").trim(),
            needsAttention: String(item.itemKind || "") === "attention",
            isDraft: false,
            createdTaskId: this.toIntOrNull(item.createdTaskId),
            availableActions: Array.isArray(item.availableActions) ? item.availableActions : [],
          };
        },
        buildAutomationMessageDraftEntry(draft) {
          if (!draft || typeof draft !== "object") return null;
          const uiPriority = String(draft.automationRuleUiPriority || "medium").trim();
          const rule = (this.metaOptions.automationRules || []).find(
            (item) => String(item.id) === String(draft.automationRuleId || "")
          ) || null;
          const eventLabel = this.automationChainLabel({
            rule: { merge_key: rule?.merge_key || "" },
            eventLabel: draft.title || draft.sourceEventType || "Черновик сообщения",
          });
          return {
            id: `automation-message-draft-${draft.id}`,
            messageDraftId: this.toIntOrNull(draft.id),
            draftKind: "message",
            touchId: this.toIntOrNull(draft.sourceTouchId),
            eventType: String(draft.sourceEventType || "").trim(),
            eventLabel,
            title: draft.title || draft.messageSubject || eventLabel,
            summary: String(draft.messageText || "").trim(),
            resultName: "",
            happenedAtRaw: draft.sourceTouchHappenedAt || draft.createdAt || null,
            ownerName: String(draft.ownerName || "").trim(),
            uiPriority,
            priorityRank: this.automationPriorityRank(uiPriority),
            rule,
            suggestedNextStep: "",
            suggestedNextStepAt: null,
            defaultTaskCategoryId: null,
            defaultCommunicationChannelId: this.toIntOrNull(draft.proposedChannelId),
            recommendedAction: String(draft.messageText || "").trim(),
            hasSuggestedNextStep: false,
            needsAttention: true,
            isDraft: true,
            messageSubject: String(draft.messageSubject || "").trim(),
            messageText: String(draft.messageText || "").trim(),
          };
        },
        compareAutomationEntries(left, right) {
          const leftRank = this.automationPriorityRank(left?.uiPriority);
          const rightRank = this.automationPriorityRank(right?.uiPriority);
          if (leftRank !== rightRank) {
            return leftRank - rightRank;
          }
          return (this.parseTaskDueTimestamp(right?.happenedAtRaw) || 0) - (this.parseTaskDueTimestamp(left?.happenedAtRaw) || 0);
        },
        automationChainLabel(item) {
          const mergeKey = String(item?.rule?.merge_key || "").trim();
          const labels = {
            email: "Email-цепочка",
            telegram: "Telegram-цепочка",
            whatsapp: "WhatsApp-цепочка",
            proposal: "КП / предложение",
            contract: "Договор",
            invoice: "Счёт / оплата",
          };
          if (labels[mergeKey]) {
            return labels[mergeKey];
          }
          return item?.eventLabel || "Цепочка";
        },
        groupAutomationEntries(items) {
          const groups = new Map();
          (Array.isArray(items) ? items : []).forEach((item) => {
            const mergeKey = String(item?.rule?.merge_key || "").trim();
            const groupKey = mergeKey || `touch-${item?.touchId || Math.random()}`;
            if (!groups.has(groupKey)) {
              groups.set(groupKey, []);
            }
            groups.get(groupKey).push(item);
          });
          return Array.from(groups.entries()).map(([groupKey, entries]) => {
            const sorted = entries.slice().sort((left, right) => (
              (this.parseTaskDueTimestamp(right.happenedAtRaw) || 0) - (this.parseTaskDueTimestamp(left.happenedAtRaw) || 0)
              || this.compareAutomationEntries(left, right)
            ));
            const primary = sorted[0] || null;
            return {
              id: `automation-chain-${groupKey}`,
              groupKey,
              title: this.automationChainLabel(primary),
              primary,
              items: sorted,
              count: sorted.length,
            };
          }).sort((left, right) => this.compareAutomationEntries(left.primary, right.primary));
        },
        resolveEventTouchAutomationEntry(eventItem) {
          const touchId = this.toIntOrNull(eventItem?.touchId);
          if (!touchId) return null;
          const touch = (this.datasets.touches || []).find((item) => String(item.id) === String(touchId));
          if (!touch) return null;
          return this.buildAutomationTouchEntry(touch);
        },
        groupDealTimelineEvents(eventItems) {
          const result = [];
          const chains = new Map();
          const eventKey = (eventItem) => {
            if (!eventItem || typeof eventItem !== "object") return "";
            return [
              this.toIntOrNull(eventItem.touchId) ? `touch:${this.toIntOrNull(eventItem.touchId)}` : "",
              this.toIntOrNull(eventItem.taskId) ? `task:${this.toIntOrNull(eventItem.taskId)}` : "",
              this.toIntOrNull(eventItem.communicationMessageId) ? `message:${this.toIntOrNull(eventItem.communicationMessageId)}` : "",
              String(eventItem.documentUrl || "").trim() ? `document:${String(eventItem.documentUrl || "").trim()}` : "",
              String(eventItem.eventType || "").trim(),
              String(eventItem.timestamp || "").trim(),
              String(eventItem.result || "").trim(),
              String(eventItem.title || "").trim(),
              String(eventItem.summaryText || "").trim(),
              String(eventItem.touchResult || "").trim(),
              String(eventItem.directionLabel || "").trim(),
            ].join("::");
          };
          (Array.isArray(eventItems) ? eventItems : []).forEach((eventItem, index) => {
            const automationEntry = this.resolveEventTouchAutomationEntry(eventItem);
            const mergeKey = String(automationEntry?.rule?.merge_key || "").trim();
            if (!mergeKey) {
              result.push({
                id: `deal-event-item-${index}`,
                type: "single",
                eventItem,
              });
              return;
            }
            const existingChain = chains.get(mergeKey);
            if (existingChain) {
              const nextKey = eventKey(eventItem);
              if (!existingChain.itemKeys.has(nextKey)) {
                existingChain.itemKeys.add(nextKey);
                existingChain.items.push(eventItem);
              }
              return;
            }
            const chain = {
              id: `deal-event-chain-${mergeKey}-${index}`,
              type: "chain",
              mergeKey,
              title: this.automationChainLabel(automationEntry),
              automationEntry,
              items: [eventItem],
              itemKeys: new Set([eventKey(eventItem)]),
            };
            chains.set(mergeKey, chain);
            result.push(chain);
          });
          result.forEach((item) => {
            if (item?.type !== "chain") return;
            item.items = (Array.isArray(item.items) ? item.items.slice() : []).sort((left, right) => (
              (this.parseTaskDueTimestamp(right?.timestamp) || 0) - (this.parseTaskDueTimestamp(left?.timestamp) || 0)
            ));
            delete item.itemKeys;
          });
          return result;
        },
        dealTimelinePrimaryEvent(item) {
          if (!item || typeof item !== "object") return null;
          return item.type === "chain" ? item.items[0] || null : item.eventItem;
        },
        dealTimelineChainSummary(item) {
          if (!item || item.type !== "chain") return "";
          const labels = (item.items || [])
            .map((entry) => entry.title || entry.result || "")
            .filter(Boolean);
          return labels.join(" • ");
        },
        managerNotificationCardClass(item) {
          const priority = String(item?.uiPriority || "").trim();
          if (priority === "critical") {
            return "border-red-400/40 bg-red-400/10";
          }
          if (priority === "high") {
            return "border-amber-400/40 bg-amber-400/10";
          }
          if (priority === "medium") {
            return "border-sky-400/30 bg-sky-400/10";
          }
          return "border-crm-border bg-[#102f4a]";
        },
        toggleManagerNotifications() {
          this.showManagerNotifications = !this.showManagerNotifications;
          if (this.showManagerNotifications) {
            this.showStatusFilter = false;
            this.showTaskCompanyFilter = false;
            this.showTaskCategoryFilter = false;
            this.showTaskDealFilter = false;
            this.showTouchCompanyFilter = false;
            this.showTouchDealFilter = false;
            this.ensureAutomationDataLoaded().catch(() => {});
            this.ensureAutomationNotificationsPolling();
            this.loadUnboundCommunications({ preserveSelection: true, silent: true }).catch(() => {});
          } else {
            this.managerNotificationDraftPreviewId = "";
            this.managerNotificationReplyDraftId = "";
            this.managerNotificationReplyComposer = {
              subject: "",
              bodyText: "",
              recipient: "",
            };
          }
        },
        closeManagerNotificationSidebar() {
          this.showManagerNotificationSidebar = false;
          this.activeManagerNotificationId = "";
          this.managerNotificationSidebarMode = "overview";
          this.activeAutomationMessageDraftPreview = null;
          this.managerNotificationReplyDraftId = "";
          this.managerNotificationDraftPreviewId = "";
          this.managerNotificationReplyComposer = {
            subject: "",
            bodyText: "",
            recipient: "",
          };
          this.resetUnboundCommunicationsState();
        },
        isManagerNotificationDraftPreviewOpen(notificationId) {
          return String(this.managerNotificationDraftPreviewId || "") === String(notificationId || "");
        },
        isManagerNotificationReplyOpen(messageDraftId) {
          return String(this.managerNotificationReplyDraftId || "") === String(messageDraftId || "");
        },
        managerNotificationReplyDraft(messageDraftId) {
          return this.getAutomationMessageDraftById(messageDraftId);
        },
        managerNotificationReplyChannel(messageDraftId) {
          const draft = this.managerNotificationReplyDraft(messageDraftId);
          if (!draft) return "";
          return this.automationEventChannelCode(draft.sourceEventType) || this.normalizeTouchChannelCode(draft.proposedChannelName);
        },
        toggleManagerNotificationDraftPreview(notificationId) {
          const normalizedId = String(notificationId || "").trim();
          if (!normalizedId) return;
          this.managerNotificationDraftPreviewId = this.isManagerNotificationDraftPreviewOpen(normalizedId) ? "" : normalizedId;
        },
        resetUnboundCommunicationsState() {
          this.isUnboundCommunicationsLoading = false;
          this.isUnboundConversationMessagesLoading = false;
          this.isUnboundConversationBinding = false;
          this.isUnboundCommunicationSending = false;
          this.unboundConversations = [];
          this.unboundConversationMessages = [];
          this.activeUnboundConversationId = null;
          this.unboundConversationBindForm = {
            clientId: null,
            contactId: null,
            dealId: null,
          };
          this.unboundCommunicationComposer = this.getDefaultCommunicationComposer(null);
        },
        syncUnboundConversationBindFormFromConversation(conversation) {
          const clientId = this.toIntOrNull(conversation?.clientId);
          const contactId = this.toIntOrNull(conversation?.contactId);
          const dealId = this.toIntOrNull(conversation?.dealId);
          this.unboundConversationBindForm = {
            clientId,
            contactId,
            dealId,
          };
        },
        async loadUnboundConversationMessages(conversationId, options = {}) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          if (!normalizedConversationId) {
            this.unboundConversationMessages = [];
            return;
          }
          if (!options.silent) {
            this.isUnboundConversationMessagesLoading = true;
          }
          try {
            const payload = await this.apiRequest(`/api/v1/communications/conversations/${normalizedConversationId}/messages/`);
            const records = Array.isArray(payload) ? payload : this.normalizePaginatedResponse(payload);
            this.unboundConversationMessages = records.map((item) => this.mapCommunicationMessage(item));
          } finally {
            this.isUnboundConversationMessagesLoading = false;
          }
        },
        async selectUnboundConversation(conversationId, options = {}) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          this.activeUnboundConversationId = normalizedConversationId;
          this.activeAutomationMessageDraftPreview = null;
          const conversation = this.activeUnboundConversation;
          this.syncUnboundConversationBindFormFromConversation(conversation);
          this.unboundCommunicationComposer = this.getDefaultCommunicationComposer(conversation);
          if (normalizedConversationId) {
            await this.loadUnboundConversationMessages(normalizedConversationId, options);
            const activeConversation = this.activeUnboundConversation;
            if (activeConversation && !String(this.unboundCommunicationComposer.bodyText || "").trim()) {
              this.unboundCommunicationComposer = this.getDefaultCommunicationComposer(activeConversation, this.unboundConversationMessages);
            }
          } else {
            this.unboundConversationMessages = [];
          }
        },
        visibleManagerNotificationActions(notification) {
          if (String(notification?.sourceType || "") === "queue" && String(notification?.queueKind || "") === "next_step") {
            return [{ id: "confirm_next_step", label: "Подтвердить" }];
          }
          const actions = Array.isArray(notification?.availableActions) ? notification.availableActions : [];
          return actions.filter((action) => {
            const actionId = String(action?.id || "").trim();
            if (actionId === "call") {
              return false;
            }
            if (actionId === "schedule_meeting") {
              return false;
            }
            if (actionId === "reply") {
              return false;
            }
            return true;
          });
        },
        managerNotificationActionLabel(action) {
          const actionId = String(action?.id || "").trim();
          if (actionId === "confirm_next_step") {
            return "Подтвердить";
          }
          if (actionId === "reply") {
            return "Заполнить результат касания";
          }
          return action?.label || "";
        },
        managerNotificationSourceLabel(notification) {
          const touchId = this.toIntOrNull(notification?.touchId || notification?.sourceTouchId);
          const summary = String(notification?.sourceTouchSummary || "").trim();
          if (touchId && summary) {
            return `Касание #${touchId}: ${summary}`;
          }
          if (touchId) {
            return `Касание #${touchId}`;
          }
          return summary;
        },
        managerNotificationContextLabel(notification) {
          if (!notification || typeof notification !== "object") return "";
          if (this.toIntOrNull(notification.dealId) && String(notification.dealTitle || "").trim()) {
            return String(notification.dealTitle || "").trim();
          }
          if (this.toIntOrNull(notification.companyId || notification.clientId) && String(notification.companyName || "").trim()) {
            return String(notification.companyName || "").trim();
          }
          if (this.toIntOrNull(notification.leadId) && String(notification.leadTitle || "").trim()) {
            return String(notification.leadTitle || "").trim();
          }
          return "";
        },
        openManagerNotificationContext(notification) {
          if (!notification || typeof notification !== "object") return;
          if (this.toIntOrNull(notification.dealId)) {
            this.showManagerNotifications = false;
            this.openDealEditorById(notification.dealId);
            return;
          }
          const companyId = this.toIntOrNull(notification.companyId || notification.clientId);
          if (companyId) {
            this.showManagerNotifications = false;
            this.openCompanyEditorById(companyId);
            return;
          }
          const leadId = this.toIntOrNull(notification.leadId);
          if (leadId) {
            const lead = (this.datasets.leads || []).find((item) => String(item.id) === String(leadId)) || null;
            if (lead) {
              this.showManagerNotifications = false;
              this.openLeadEditor(lead);
            }
          }
        },
        managerNotificationReplyState(notification) {
          const queueId = this.toIntOrNull(notification?.sourceId);
          if (!queueId) return "";
          return String(this.managerNotificationReplyStates[String(queueId)] || "").trim();
        },
        managerNotificationTouchHasResult(notification) {
          const touchId = this.toIntOrNull(notification?.touchId || notification?.sourceTouchId);
          if (!touchId) return false;
          const touch = (this.datasets.touches || []).find((item) => String(item.id) === String(touchId)) || null;
          if (!touch) return false;
          return !!(
            this.toIntOrNull(touch.resultOptionId)
            || String(touch.resultOptionName || "").trim()
            || String(touch.resultOptionCode || "").trim()
          );
        },
        managerNotificationReplyButtonVisible(notification) {
          if (String(notification?.sourceType || "") !== "queue") return false;
          if (String(notification?.queueKind || "") === "next_step") return false;
          if (this.managerNotificationTouchHasResult(notification)) return true;
          if (this.managerNotificationReplyState(notification) === "answered") return true;
          return !!this.toIntOrNull(notification?.touchId || notification?.sourceTouchId);
        },
        managerNotificationReplyButtonLabel(notification) {
          return (this.managerNotificationTouchHasResult(notification) || this.managerNotificationReplyState(notification) === "answered")
            ? "Результат касания заполнен"
            : "Заполнить результат касания";
        },
        managerNotificationReplyButtonDisabled() {
          return false;
        },
        managerNotificationReplyChannelCode(notification) {
          const touchId = this.toIntOrNull(notification?.touchId || notification?.sourceTouchId);
          const touch = touchId
            ? ((this.datasets.touches || []).find((item) => String(item.id) === String(touchId)) || null)
            : null;
          const touchChannel = touch?.channelId
            ? ((this.metaOptions.communicationChannels || []).find((item) => String(item.id) === String(touch.channelId)) || null)
            : null;
          return this.normalizeTouchChannelCode(touchChannel)
            || this.automationEventChannelCode(notification?.eventType)
            || "";
        },
        managerNotificationMessageReplyButtonVisible(notification) {
          if (String(notification?.sourceType || "") !== "queue") return false;
          if (String(notification?.queueKind || "") === "next_step") return false;
          const channelCode = this.managerNotificationReplyChannelCode(notification);
          if (!["email", "telegram"].includes(channelCode)) {
            return false;
          }
          return !!(
            this.toIntOrNull(notification?.messageDraftId)
            || this.toIntOrNull(notification?.conversationId)
            || this.toIntOrNull(notification?.dealId)
          );
        },
        managerNotificationMessageReplyButtonDisabled(notification) {
          return this.isManagerNotificationReplySending && String(this.activeManagerNotificationId || "") === String(notification?.id || "");
        },
        setManagerNotificationReplyState(queueId, state) {
          const normalizedQueueId = this.toIntOrNull(queueId);
          if (!normalizedQueueId) return;
          this.managerNotificationReplyStates = {
            ...this.managerNotificationReplyStates,
            [String(normalizedQueueId)]: String(state || "").trim(),
          };
        },
        clearManagerNotificationReplyState(queueId) {
          const normalizedQueueId = this.toIntOrNull(queueId);
          if (!normalizedQueueId) return;
          const nextStates = { ...(this.managerNotificationReplyStates || {}) };
          delete nextStates[String(normalizedQueueId)];
          this.managerNotificationReplyStates = nextStates;
        },
        notificationNeedsBinding(notification) {
          if (!notification || String(notification.sourceType || "") !== "queue") return false;
          const hasClient = !!this.toIntOrNull(notification.clientId || notification.companyId);
          const hasDeal = !!this.toIntOrNull(notification.dealId);
          return !hasClient && !hasDeal && !!this.toIntOrNull(notification.messageDraftId);
        },
        async openManagerNotificationSidebar(notification, mode = "overview") {
          if (!notification) return;
          this.showManagerNotifications = false;
          this.showManagerNotificationSidebar = true;
          this.activeManagerNotificationId = String(notification.id || "").trim();
          this.managerNotificationSidebarMode = String(mode || "overview").trim() || "overview";
          this.managerNotificationDraftPreviewId = "";
          this.managerNotificationReplyDraftId = "";
          this.activeAutomationMessageDraftPreview = null;
          const draft = this.getAutomationMessageDraftById(notification.messageDraftId);
          const conversationId = this.toIntOrNull(draft?.conversationId) || this.toIntOrNull(notification?.conversationId);
          if (draft) {
            const previewPayload = {
              id: draft.id,
              title: draft.title || draft.messageSubject || "Сообщение",
              messageText: String(draft.messageText || "").trim(),
            };
            this.activeAutomationMessageDraftPreview = previewPayload;
            this.initializeManagerNotificationReplyComposer(draft);
          } else {
            this.managerNotificationReplyComposer = {
              subject: "",
              bodyText: "",
              recipient: "",
            };
          }
          if (conversationId) {
            await this.loadUnboundCommunications({ preserveSelection: false, forceReloadMessages: false, silent: true });
            await this.ensureUnboundConversationAvailable(conversationId);
            await this.selectUnboundConversation(conversationId, { silent: true });
            if (draft && !String(this.managerNotificationReplyComposer.recipient || "").trim()) {
              this.managerNotificationReplyComposer = {
                ...this.managerNotificationReplyComposer,
                recipient: this.deriveConversationRecipientFromMessages(this.activeUnboundConversation, this.unboundConversationMessages),
              };
            }
          } else {
            this.resetUnboundCommunicationsState();
          }
          if (mode === "reply" && draft) {
            this.managerNotificationReplyDraftId = this.toIntOrNull(draft.id);
            this.$nextTick(() => {
              const panel = document.querySelector("[data-manager-sidebar-reply]");
              if (panel && typeof panel.scrollIntoView === "function") {
                panel.scrollIntoView({ behavior: "smooth", block: "start" });
              }
            });
          }
          if (mode === "binding") {
            this.$nextTick(() => {
              const panel = document.querySelector("[data-manager-sidebar-binding]");
              if (panel && typeof panel.scrollIntoView === "function") {
                panel.scrollIntoView({ behavior: "smooth", block: "start" });
              }
            });
          }
        },
        async loadUnboundCommunications(options = {}) {
          const previousConversationId = this.toIntOrNull(this.activeUnboundConversationId);
          if (!options.silent) {
            this.isUnboundCommunicationsLoading = true;
          }
          try {
            const payload = await this.apiRequest("/api/v1/communications/conversations/?requires_manual_binding=true&page_size=100");
            const records = this.normalizePaginatedResponse(payload)
              .map((item) => this.mapConversation(item))
              .filter((item) => item.requiresManualBinding);
            this.unboundConversations = records;
            let nextConversationId = options.preserveSelection ? previousConversationId : null;
            if (!nextConversationId || !records.some((item) => String(item.id) === String(nextConversationId))) {
              nextConversationId = records[0]?.id || null;
            }
            const shouldReloadMessages = !!nextConversationId && (
              options.forceReloadMessages
              || String(nextConversationId) !== String(previousConversationId || "")
              || !this.unboundConversationMessages.length
            );
            this.activeUnboundConversationId = nextConversationId;
            this.syncUnboundConversationBindFormFromConversation(this.activeUnboundConversation);
            if (shouldReloadMessages) {
              await this.loadUnboundConversationMessages(nextConversationId, { silent: options.silent });
            } else if (!nextConversationId) {
              this.unboundConversationMessages = [];
            }
          } finally {
            this.isUnboundCommunicationsLoading = false;
          }
        },
        async ensureUnboundConversationAvailable(conversationId) {
          const normalizedConversationId = this.toIntOrNull(conversationId);
          if (!normalizedConversationId) return null;
          let conversation = (this.unboundConversations || []).find((item) => String(item.id) === String(normalizedConversationId)) || null;
          if (conversation) return conversation;
          conversation = await this.fetchConversationById(normalizedConversationId);
          if (!conversation) return null;
          this.unboundConversations = [conversation, ...(this.unboundConversations || []).filter((item) => String(item.id) !== String(normalizedConversationId))];
          return conversation;
        },
        async bindSelectedUnboundConversation() {
          const conversationId = this.toIntOrNull(this.activeUnboundConversationId);
          if (!conversationId || this.isUnboundConversationBinding) return;
          this.clearUiErrors({ modalOnly: true });
          this.isUnboundConversationBinding = true;
          try {
            const clientId = this.toIntOrNull(this.unboundConversationBindForm.clientId);
            const contactId = this.toIntOrNull(this.unboundConversationBindForm.contactId);
            const dealId = this.toIntOrNull(this.unboundConversationBindForm.dealId);
            const boundConversation = this.mapConversation(await this.apiRequest(`/api/v1/communications/conversations/${conversationId}/bind/`, {
              method: "POST",
              body: {
                client: clientId,
                contact: contactId,
                deal: dealId,
              }
            }));
            await this.loadUnboundCommunications({ preserveSelection: false, forceReloadMessages: true, silent: true });
            await Promise.all([
              this.loadAutomationQueue(),
              this.loadAutomationMessageDrafts(),
              this.loadAutomationDrafts(),
            ]);
            if (this.toIntOrNull(boundConversation.dealId)) {
              this.closeManagerNotificationSidebar();
              const deal = await this.fetchDealById(boundConversation.dealId);
              this.openDealEditor(deal);
              this.showDealCommunicationsPanel = true;
              await this.loadDealCommunications({ preserveSelection: false, forceReloadMessages: true });
              await this.selectDealConversation(boundConversation.id, { silent: true });
              return;
            }
            if (this.toIntOrNull(boundConversation.clientId)) {
              this.closeManagerNotificationSidebar();
              this.openCompanyEditorById(boundConversation.clientId);
              this.showCompanyCommunicationsPanel = true;
              await this.loadCompanyCommunications({ preserveSelection: false, forceReloadMessages: true });
              await this.selectCompanyConversation(boundConversation.id, { silent: true });
            }
          } catch (error) {
            this.setUiError(`Ошибка привязки переписки: ${error.message}`, { modal: true });
          } finally {
            this.isUnboundConversationBinding = false;
          }
        },
        async openActiveUnboundConversationContext() {
          const conversation = this.activeUnboundConversation;
          if (!conversation) return;
          this.showManagerNotifications = false;
          if (this.toIntOrNull(conversation.dealId)) {
            const deal = await this.fetchDealById(conversation.dealId);
            this.openDealEditor(deal);
            this.showDealCommunicationsPanel = true;
            await this.loadDealCommunications({ preserveSelection: false, forceReloadMessages: true });
            await this.selectDealConversation(conversation.id, { silent: true });
            return;
          }
          if (this.toIntOrNull(conversation.clientId)) {
            this.openCompanyEditorById(conversation.clientId);
            this.showCompanyCommunicationsPanel = true;
            await this.loadCompanyCommunications({ preserveSelection: false, forceReloadMessages: true });
            await this.selectCompanyConversation(conversation.id, { silent: true });
          }
        },
        scrollToUnboundBinding() {
          this.$nextTick(() => {
            const panel = document.querySelector("[data-unbound-binding-block]");
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
        },
        async openNotificationBinding(notification) {
          if (!this.notificationNeedsBinding(notification)) return;
          const draft = this.getAutomationMessageDraftById(notification.messageDraftId);
          if (!this.toIntOrNull(draft?.conversationId)) {
            this.setUiError("Не удалось определить переписку для привязки.", { modal: true });
            return;
          }
          await this.openManagerNotificationSidebar(notification, "binding");
        },
        async openManagerNotification(item) {
          if (!item) return;
          if (this.toIntOrNull(item.messageDraftId) || this.notificationNeedsBinding(item)) {
            await this.openManagerNotificationSidebar(item, "overview");
            return;
          }
          this.showManagerNotifications = false;
          if (item.sourceType === "message_draft" && item.sourceId) {
            await this.previewAutomationMessageDraft(item.sourceId);
            return;
          }
          if (item.sourceType === "queue" && String(item.queueKind || "") === "next_step") {
            this.openAutomationTaskAction(item, {
              title: item.recommendedAction || item.title || "",
              taskCategoryId: this.toIntOrNull(item.defaultTaskCategoryId),
            });
            return;
          }
          if (item.sourceType === "queue" && item.touchId) {
            const shouldPromptResult = this.visibleManagerNotificationActions(item)
              .some((action) => String(action?.id || "").trim() === "reply");
            if (shouldPromptResult) {
              await this.openTouchWithResultPrompt(
                item.touchId,
                "Сначала заполните результат входящего касания, затем при необходимости ответьте клиенту."
              );
              return;
            }
            await this.openTouchFromEvent(item.touchId);
            return;
          }
          if (item.sourceType === "draft" && item.touchId) {
            await this.openTouchFromEvent(item.touchId);
            return;
          }
          if (item.sourceType === "touch" && item.sourceId) {
            await this.openTouchFromEvent(item.sourceId);
          }
        },
        async openManagerNotificationReply(notification) {
          if (!notification) return;
          this.showManagerNotifications = false;
          if (this.toIntOrNull(notification.messageDraftId) || this.toIntOrNull(notification.conversationId)) {
            await this.openManagerNotificationSidebar(notification, "reply");
            return;
          }
          const channelCode = this.managerNotificationReplyChannelCode(notification) || "email";
          const dealId = this.toIntOrNull(notification.dealId);
          if (dealId) {
            try {
              const deal = await this.fetchDealById(dealId);
              const touchId = this.toIntOrNull(notification.touchId || notification.sourceTouchId);
              const touch = touchId
                ? ((this.datasets.touches || []).find((item) => String(item.id) === String(touchId)) || null)
                : null;
              const defaultForm = this.getDefaultDealCommunicationStartForm();
              this.showManagerNotifications = false;
              this.openDealEditor(deal);
              this.showDealCommunicationsPanel = true;
              this.showDealCommunicationStartForm = true;
              this.dealCommunicationStartForm = {
                ...defaultForm,
                channel: channelCode,
                contactId: this.toIntOrNull(notification.contactId || touch?.contactId || defaultForm.contactId),
                recipient: this.deriveCommunicationRecipient(channelCode, notification.contactId || touch?.contactId || defaultForm.contactId),
                subject: channelCode === "email"
                  ? (String(defaultForm.subject || "").trim() || String(touch?.summary || notification.title || "").trim())
                  : "",
                bodyText: "",
              };
              if (!String(this.dealCommunicationStartForm.recipient || "").trim()) {
                this.syncDealCommunicationStartRecipient();
              }
              this.scrollToCommunicationComposer("deal");
            } catch (error) {
              this.setUiError(`Ошибка подготовки ответа: ${error.message}`, { modal: true });
            }
            return;
          }
          this.setUiError("Для этого уведомления пока не удалось открыть ответ в переписке.", { modal: true });
        },
        async confirmAutomationQueueItem(queueId) {
          const normalizedQueueId = this.toIntOrNull(queueId);
          if (!normalizedQueueId) return;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.apiRequest(`/api/v1/automation-queue/${normalizedQueueId}/confirm/`, {
              method: "POST",
              body: {},
            });
            await Promise.all([
              this.loadAutomationQueue(),
              this.loadAutomationMessageDrafts(),
              this.loadSection("tasks"),
              this.loadSection("touches"),
              this.loadSection("deals"),
              this.loadSection("companies"),
              this.loadSection("leads"),
            ]);
          } catch (error) {
            this.setUiError(`Ошибка обработки очереди: ${error.message}`, { modal: true });
          }
        },
        async dismissAutomationQueueItem(queueId) {
          const normalizedQueueId = this.toIntOrNull(queueId);
          if (!normalizedQueueId) return;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.apiRequest(`/api/v1/automation-queue/${normalizedQueueId}/dismiss/`, {
              method: "POST",
              body: {},
            });
            await Promise.all([this.loadAutomationQueue(), this.loadAutomationMessageDrafts()]);
          } catch (error) {
            this.setUiError(`Ошибка отклонения элемента очереди: ${error.message}`, { modal: true });
          }
        },
        findCommunicationChannelByCode(channelCode) {
          const normalizedCode = this.normalizeTouchChannelCode(channelCode);
          if (!normalizedCode) return null;
          return (this.metaOptions.communicationChannels || []).find(
            (item) => this.normalizeTouchChannelCode(item) === normalizedCode
          ) || null;
        },
        async openTouchWithResultPrompt(touchId, promptText = "Заполните результат касания") {
          const normalizedTouchId = this.toIntOrNull(touchId);
          if (!normalizedTouchId) return;
          await this.openTouchFromEvent(normalizedTouchId);
          this.setTouchResultPrompt(promptText);
        },
        openContactEditorById(contactId) {
          const normalizedId = this.toIntOrNull(contactId);
          if (!normalizedId) return;
          const contact = (this.datasets.contacts || []).find((item) => String(item.id) === String(normalizedId));
          if (contact) {
            this.openContactEditor(contact);
          }
        },
        openCompanyEditorById(companyId) {
          const normalizedId = this.toIntOrNull(companyId);
          if (!normalizedId) return;
          const company = (this.datasets.companies || []).find((item) => String(item.id) === String(normalizedId));
          if (company) {
            this.openCompanyEditor(company);
          }
        },
        touchOwnerIdByDealId(dealId) {
          const normalizedDealId = this.toIntOrNull(dealId);
          if (!normalizedDealId) return null;
          const deal = (this.datasets.deals || []).find((item) => String(item.id) === String(normalizedDealId));
          return this.toIntOrNull(deal?.ownerId);
        },
        touchOwnerIdByLeadId(leadId) {
          const normalizedLeadId = this.toIntOrNull(leadId);
          if (!normalizedLeadId) return null;
          const lead = (this.datasets.leads || []).find((item) => String(item.id) === String(normalizedLeadId));
          return this.toIntOrNull(lead?.assignedToId);
        },
        touchOwnerIdByCompanyId(companyId) {
          const normalizedCompanyId = this.toIntOrNull(companyId);
          if (!normalizedCompanyId) return null;
          const activeDeals = (this.datasets.deals || [])
            .filter((deal) => (
              String(deal.clientId || "") === String(normalizedCompanyId)
              && this.getDealStatusBucket(deal) !== "done"
            ))
            .slice()
            .sort((left, right) => {
              const leftTs = this.parseTaskDueTimestamp(left.closeDate) || Number.MAX_SAFE_INTEGER;
              const rightTs = this.parseTaskDueTimestamp(right.closeDate) || Number.MAX_SAFE_INTEGER;
              return leftTs - rightTs || Number(left.id || 0) - Number(right.id || 0);
            });
          const dealOwnerId = this.toIntOrNull(activeDeals.find((deal) => this.toIntOrNull(deal.ownerId))?.ownerId);
          if (dealOwnerId) {
            return dealOwnerId;
          }
          const activeLeadCodes = new Set(["new", "in_progress", "attempting_contact", "qualified"]);
          const activeLead = (this.datasets.leads || []).find((lead) => (
            String(lead.clientId || "") === String(normalizedCompanyId)
            && activeLeadCodes.has(String(lead.statusCode || lead.status || "").trim())
            && this.toIntOrNull(lead.assignedToId)
          ));
          return this.toIntOrNull(activeLead?.assignedToId);
        },
        touchOwnerIdByTaskId(taskId) {
          const normalizedTaskId = this.toIntOrNull(taskId);
          if (!normalizedTaskId) return null;
          const task = (this.datasets.tasks || []).find((item) => String(item.id) === String(normalizedTaskId));
          if (!task) return null;
          return (
            this.touchOwnerIdByDealId(task.dealId)
            || this.touchOwnerIdByLeadId(task.leadId)
            || this.touchOwnerIdByCompanyId(task.clientId)
          );
        },
        resolveTouchOwnerIdFromContext(context = {}) {
          const dealId = this.toIntOrNull(context.dealId);
          const leadId = this.toIntOrNull(context.leadId);
          const taskId = this.toIntOrNull(context.taskId);
          const companyId = this.toIntOrNull(context.companyId);
          return (
            this.touchOwnerIdByDealId(dealId)
            || this.touchOwnerIdByLeadId(leadId)
            || this.touchOwnerIdByTaskId(taskId)
            || this.touchOwnerIdByCompanyId(companyId)
            || null
          );
        },
        applyTouchOwnerFromContext() {
          if (this.activeSection !== "touches") {
            return;
          }
          const resolvedOwnerId = this.resolveTouchOwnerIdFromContext({
            dealId: this.forms.touches.dealId,
            leadId: this.forms.touches.leadId,
            taskId: this.forms.touches.taskId,
            companyId: this.forms.touches.companyId,
          });
          if (resolvedOwnerId) {
            this.forms.touches.ownerId = resolvedOwnerId;
          }
        },
        automationEventChannelCode(eventType) {
          const raw = String(eventType || "").trim().toLowerCase();
          if (!raw) return "";
          if (raw.startsWith("email_")) return "email";
          if (raw.startsWith("telegram_")) return "telegram";
          if (raw.startsWith("whatsapp_")) return "whatsapp";
          if (raw.startsWith("call_")) return "call";
          if (raw.startsWith("meeting_")) return "meeting";
          if (raw.startsWith("proposal_")) return "proposal";
          if (raw.startsWith("contract_") || raw.startsWith("invoice_")) return "documents";
          return "";
        },
        openAutomationTouchAction(item, { channelCode = "", direction = "outgoing", summary = "" } = {}) {
          this.activeSection = "touches";
          this.openCreateModal();
          const resolvedCompanyId = this.toIntOrNull(item?.clientId || item?.companyId);
          const resolvedDealId = this.toIntOrNull(item?.dealId);
          const resolvedLeadId = this.toIntOrNull(item?.leadId);
          const channel = this.findCommunicationChannelByCode(channelCode || this.automationEventChannelCode(item?.eventType));
          this.forms.touches = {
            ...this.getDefaultForm("touches"),
            happenedAt: this.toDateTimeLocal(new Date().toISOString()),
            channelId: this.toIntOrNull(channel?.id),
            direction: direction || "outgoing",
            summary: String(summary || "").trim(),
            ownerId: this.toIntOrNull(item?.ownerId) || this.resolveTouchOwnerIdFromContext({
              dealId: resolvedDealId,
              leadId: resolvedLeadId,
              companyId: resolvedCompanyId,
            }),
            companyId: resolvedCompanyId,
            contactId: this.toIntOrNull(item?.contactId),
            taskId: null,
            leadId: resolvedLeadId,
            dealId: resolvedDealId,
            documentUploadTarget: resolvedDealId ? "deal" : (resolvedCompanyId ? "company" : ""),
          };
          this.showModal = true;
          this.loadTouchDocuments();
          this.$nextTick(() => this.applyTouchAutomationRule());
        },
        initializeManagerNotificationReplyComposer(draft) {
          const channelCode = this.automationEventChannelCode(draft?.sourceEventType) || this.normalizeTouchChannelCode(draft?.proposedChannelName);
          this.managerNotificationReplyComposer = {
            subject: String(draft?.messageSubject || "").trim(),
            bodyText: "",
            recipient: this.deriveCommunicationRecipient(channelCode, draft?.contactId),
          };
        },
        scrollToCommunicationComposer(target) {
          const selectorMap = {
            unbound: {
              panel: "[data-unbound-communication-composer]",
              body: "[data-unbound-communication-body]",
            },
            deal: {
              panel: "[data-deal-communication-composer]",
              body: "[data-deal-communication-body]",
            },
            company: {
              panel: "[data-company-communication-composer]",
              body: "[data-company-communication-body]",
            },
          };
          const selectors = selectorMap[String(target || "").trim()];
          if (!selectors) return;
          this.$nextTick(() => {
            const panel = document.querySelector(selectors.panel);
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
            window.setTimeout(() => {
              const body = document.querySelector(selectors.body);
              if (body && typeof body.focus === "function") {
                body.focus();
              }
            }, 180);
          });
        },
        async openAutomationMessageReply(messageDraftId) {
          const draft = this.getAutomationMessageDraftById(messageDraftId);
          if (!draft) return;
          const notification = (this.managerNotifications || []).find(
            (item) => String(item.messageDraftId || "") === String(draft.id || "")
          ) || null;
          if (notification) {
            await this.openManagerNotificationSidebar(notification, "reply");
            return;
          }
          const normalizedDraftId = this.toIntOrNull(messageDraftId);
          if (!normalizedDraftId) return;
          this.managerNotificationReplyDraftId = normalizedDraftId;
          this.initializeManagerNotificationReplyComposer(draft);
        },
        async previewAutomationMessageDraft(messageDraftId) {
          const draft = this.getAutomationMessageDraftById(messageDraftId);
          if (!draft) return "";
          const conversationId = this.toIntOrNull(draft.conversationId);
          const channelCode = this.automationEventChannelCode(draft.sourceEventType) || this.normalizeTouchChannelCode(draft.proposedChannelName);
          const recipient = this.deriveCommunicationRecipient(channelCode, draft.contactId);
          const previewPayload = {
            id: draft.id,
            title: draft.title || draft.messageSubject || "Черновик сообщения",
            messageText: String(draft.messageText || "").trim(),
          };

          if (conversationId) {
            const conversation = await this.fetchConversationById(conversationId);
            const dealId = this.toIntOrNull(conversation.dealId || draft.dealId);
            const companyId = this.toIntOrNull(conversation.clientId || draft.clientId);
            if (dealId) {
              this.showManagerNotifications = false;
              const deal = await this.fetchDealById(dealId);
              this.openDealEditor(deal);
              this.showDealCommunicationsPanel = true;
              await this.loadDealCommunications({ preserveSelection: false, forceReloadMessages: true });
              await this.selectDealConversation(conversationId, { silent: true });
              this.dealCommunicationComposer = {
                subject: String(draft.messageSubject || "").trim(),
                bodyText: String(draft.messageText || "").trim(),
                recipient: recipient,
              };
              this.activeAutomationMessageDraftPreview = previewPayload;
              this.ensureCommunicationsPolling();
              return "deal";
            }
            if (companyId) {
              const company = (this.datasets.companies || []).find((item) => String(item.id) === String(companyId));
              if (company) {
                this.showManagerNotifications = false;
                this.openCompanyEditor(company);
                this.showCompanyCommunicationsPanel = true;
                await this.loadCompanyCommunications({ preserveSelection: false, forceReloadMessages: true });
                await this.selectCompanyConversation(conversationId, { silent: true });
                this.companyCommunicationComposer = {
                  subject: String(draft.messageSubject || "").trim(),
                  bodyText: String(draft.messageText || "").trim(),
                  recipient: recipient,
                };
                this.activeAutomationMessageDraftPreview = previewPayload;
                this.ensureCommunicationsPolling();
                return "company";
              }
            }

            this.showManagerNotifications = true;
            await this.loadUnboundCommunications({ preserveSelection: false, forceReloadMessages: true, silent: true });
            await this.selectUnboundConversation(conversationId, { silent: true });
            this.unboundCommunicationComposer = {
              subject: String(draft.messageSubject || "").trim(),
              bodyText: String(draft.messageText || "").trim(),
              recipient,
            };
            this.activeAutomationMessageDraftPreview = previewPayload;
            return "unbound";
          }

          if (this.toIntOrNull(draft.dealId)) {
            this.showManagerNotifications = false;
            const deal = await this.fetchDealById(draft.dealId);
            this.openDealEditor(deal);
            this.showDealCommunicationsPanel = true;
            this.showDealCommunicationStartForm = true;
            this.dealCommunicationStartForm = {
              channel: channelCode || "email",
              contactId: this.toIntOrNull(draft.contactId),
              recipient,
              subject: String(draft.messageSubject || "").trim(),
              bodyText: String(draft.messageText || "").trim(),
            };
            this.activeAutomationMessageDraftPreview = previewPayload;
            return "deal";
          }

          if (draft.sourceTouchId) {
            this.showManagerNotifications = false;
            await this.openTouchFromEvent(draft.sourceTouchId);
            return "touch";
          }
          return "";
        },
        openAutomationTaskAction(item, { title = "", taskCategoryId = null, channelCode = "", dueAt = "", fallbackToRecommendation = true } = {}) {
          const normalizedDealId = this.toIntOrNull(item?.dealId);
          const normalizedLeadId = this.toIntOrNull(item?.leadId);
          const normalizedCompanyId = this.toIntOrNull(item?.clientId || item?.companyId);
          const explicitTitle = String(title || "").trim();
          const resolvedTitle = explicitTitle || (
            fallbackToRecommendation
              ? String(item?.recommendedAction || item?.title || "").trim()
              : ""
          );
          const resolvedDueAt = dueAt || item?.suggestedNextStepAt || item?.deadline || "";
          const resolvedTaskCategoryId = this.toIntOrNull(taskCategoryId)
            || this.toIntOrNull(item?.defaultTaskCategoryId)
            || this.findPreferredTaskCategoryId({
              usesCommunicationChannel: !!channelCode,
              requiresFollowUp: !channelCode,
              satisfiesDealNextStepRequirement: !!channelCode,
            });
          const selectedCategory = this.resolveTaskCategoryById(resolvedTaskCategoryId);
          const communicationChannelId = this.taskCategoryUsesCommunicationChannel(selectedCategory)
            ? this.toIntOrNull(this.findCommunicationChannelByCode(channelCode)?.id)
            : null;
          if (normalizedDealId) {
            this.openDealEditorById(normalizedDealId);
            this.prepareDealTaskFromAutomation({
              title: resolvedTitle,
              recommendedAction: resolvedTitle,
              at: resolvedDueAt,
              taskCategoryId: resolvedTaskCategoryId,
              communicationChannelId,
              leadId: normalizedLeadId,
              companyId: normalizedCompanyId,
            });
            return;
          }
          this.activeSection = "tasks";
          this.openCreateModal();
          this.forms.tasks = {
            ...this.getDefaultForm("tasks"),
            subject: resolvedTitle,
            taskCategoryId: resolvedTaskCategoryId,
            taskTypeId: null,
            communicationChannelId,
            priority: "medium",
            companyId: normalizedCompanyId,
            leadId: normalizedLeadId,
            dealId: normalizedDealId,
            // `related_touch` in the activities API points to legacy Activity entries,
            // while automation notifications are sourced from Touch records.
            // Passing Touch ids here breaks task creation with a validation error.
            relatedTouchId: null,
            dueAt: resolvedDueAt ? this.toDateTimeLocal(resolvedDueAt) : "",
            reminderOffsetMinutes: 30,
            checklist: [],
            description: "",
            result: "",
            saveCompanyNote: false,
            companyNote: "",
            status: "todo",
          };
          this.taskChecklistHideCompleted = false;
          this.showModal = true;
        },
        handleAutomationQuickAction(item, actionId) {
          const normalizedActionId = String(actionId || "").trim();
          if (!normalizedActionId || !item) return;
          this.showManagerNotifications = false;
          if (normalizedActionId === "confirm_next_step") {
            if (String(item.sourceType || "") === "queue" && this.toIntOrNull(item.sourceId)) {
              this.confirmAutomationQueueItem(item.sourceId);
            }
            return;
          }
          if (normalizedActionId === "reply") {
            if (this.toIntOrNull(item.touchId)) {
              this.openTouchWithResultPrompt(item.touchId, "Сначала заполните результат входящего касания, затем при необходимости ответьте клиенту.");
              return;
            }
            this.openAutomationTouchAction(item, {
              channelCode: this.automationEventChannelCode(item.eventType),
              direction: "outgoing",
            });
            return;
          }
          if (normalizedActionId === "call") {
            this.openAutomationTouchAction(item, { channelCode: "call", direction: "outgoing" });
            return;
          }
          if (normalizedActionId === "check_email") {
            if (this.toIntOrNull(item.contactId)) {
              this.openContactEditorById(item.contactId);
              return;
            }
            if (this.toIntOrNull(item.companyId || item.clientId)) {
              this.openCompanyEditorById(item.companyId || item.clientId);
            }
            return;
          }
          if (normalizedActionId === "resend_message") {
            this.openAutomationTouchAction(item, {
              channelCode: this.automationEventChannelCode(item.eventType),
              direction: "outgoing",
            });
            return;
          }
          if (normalizedActionId === "schedule_meeting") {
            this.openAutomationTaskAction(item, {
              title: "Назначить встречу",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: true,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: true,
              }),
              channelCode: "meeting",
            });
            return;
          }
          if (normalizedActionId === "reschedule_meeting") {
            this.openAutomationTaskAction(item, {
              title: "Перенести встречу",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: true,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: true,
              }),
              channelCode: "meeting",
            });
            return;
          }
          if (normalizedActionId === "create_task") {
            this.openAutomationTaskAction(item, {
              title: "",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
              fallbackToRecommendation: false,
            });
            return;
          }
          if (normalizedActionId === "change_channel") {
            this.openAutomationTaskAction(item, {
              title: "Сменить канал связи",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
            });
            return;
          }
          if (normalizedActionId === "send_proposal") {
            this.openAutomationTaskAction(item, {
              title: "Подготовить КП",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
            });
            return;
          }
          if (normalizedActionId === "send_materials") {
            this.openAutomationTaskAction(item, {
              title: "Отправить материалы",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
            });
            return;
          }
          if (normalizedActionId === "revise_proposal") {
            this.openAutomationTaskAction(item, {
              title: "Скорректировать КП",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
            });
            return;
          }
          if (normalizedActionId === "prepare_documents") {
            this.openAutomationTaskAction(item, {
              title: "Подготовить документы",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
            });
            return;
          }
          if (normalizedActionId === "prepare_contract") {
            this.openAutomationTaskAction(item, {
              title: "Подготовить договор",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
            });
            return;
          }
          if (normalizedActionId === "issue_invoice") {
            this.openAutomationTaskAction(item, {
              title: "Выставить счёт",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
            });
            return;
          }
          if (normalizedActionId === "launch_project") {
            this.openAutomationTaskAction(item, {
              title: "Запустить оказание услуги / проект",
              taskCategoryId: this.findPreferredTaskCategoryId({
                usesCommunicationChannel: false,
                requiresFollowUp: false,
                satisfiesDealNextStepRequirement: false,
              }),
            });
          }
        },
        async confirmAutomationMessageDraft(messageDraftId) {
          const normalizedDraftId = this.toIntOrNull(messageDraftId);
          if (!normalizedDraftId) return;
          this.clearUiErrors({ modalOnly: true });
          try {
            const response = await this.apiRequest(`/api/v1/automation-message-drafts/${normalizedDraftId}/confirm/`, {
              method: "POST",
              body: {},
            });
            await this.loadAutomationMessageDrafts();
            const outboundStatus = String(response?.last_outbound_status || "").trim();
            const outboundChannel = String(response?.last_outbound_channel || "").trim();
            const outboundRecipient = String(response?.last_outbound_recipient || "").trim();
            const outboundError = String(response?.last_outbound_error || "").trim();
            if (outboundStatus === "manual_required") {
              const channelLabel = outboundChannel || "выбранного канала";
              const recipientLabel = outboundRecipient ? ` Получатель: ${outboundRecipient}.` : "";
              this.setUiError(
                `Черновик сообщения подтверждён. Для канала ${channelLabel} нужна ручная отправка.${recipientLabel}`,
                { modal: true }
              );
            } else if (outboundStatus === "failed" && outboundError) {
              this.setUiError(`Черновик сообщения подтверждён, но отправка не выполнена: ${outboundError}`, {
                modal: true,
              });
            }
          } catch (error) {
            this.setUiError(`Ошибка подтверждения черновика сообщения: ${error.message}`, { modal: true });
          }
        },
        async dismissAutomationMessageDraft(messageDraftId) {
          const normalizedDraftId = this.toIntOrNull(messageDraftId);
          if (!normalizedDraftId) return;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.apiRequest(`/api/v1/automation-message-drafts/${normalizedDraftId}/dismiss/`, {
              method: "POST",
              body: {},
            });
            await this.loadAutomationMessageDrafts();
          } catch (error) {
            this.setUiError(`Ошибка отклонения черновика сообщения: ${error.message}`, { modal: true });
          }
        },
        async sendManagerNotificationReply(messageDraftId) {
          this.clearUiErrors({ modalOnly: true });
          if (this.isManagerNotificationReplySending) return;
          const normalizedDraftId = this.toIntOrNull(messageDraftId || this.managerNotificationReplyDraftId);
          const draft = normalizedDraftId ? this.getAutomationMessageDraftById(normalizedDraftId) : null;
          if (normalizedDraftId && !draft) {
            this.setUiError("Черновик ответа не найден. Обновите уведомления и попробуйте снова.", { modal: true });
            return;
          }
          const conversationId = this.toIntOrNull(draft?.conversationId)
            || this.toIntOrNull(this.activeUnboundConversationId)
            || this.toIntOrNull(this.activeManagerNotification?.conversationId);
          if (!conversationId) {
            this.setUiError("Не удалось определить диалог для ответа. Сначала откройте или привяжите переписку.", { modal: true });
            return;
          }
          if (!String(this.managerNotificationReplyComposer.bodyText || "").trim()) {
            this.setUiError("Введите текст ответа.", { modal: true });
            return;
          }
          this.isManagerNotificationReplySending = true;
          try {
            const response = await this.apiRequest(`/api/v1/communications/conversations/${conversationId}/send/`, {
              method: "POST",
              body: {
                subject: this.managerNotificationReplyComposer.subject,
                body_text: this.managerNotificationReplyComposer.bodyText,
                recipient: this.managerNotificationReplyComposer.recipient,
              }
            });
            const messageStatus = String(response?.status || "").trim();
            const queueId = this.toIntOrNull(this.activeManagerNotification?.sourceId);
            if (messageStatus === "sent") {
              if (draft) {
                await this.apiRequest(`/api/v1/automation-message-drafts/${draft.id}/dismiss/`, {
                  method: "POST",
                  body: {},
                });
              }
              if (queueId) {
                this.setManagerNotificationReplyState(queueId, "answered");
              }
              this.managerNotificationReplyDraftId = "";
              this.managerNotificationDraftPreviewId = "";
              this.managerNotificationReplyComposer = {
                subject: "",
                bodyText: "",
                recipient: "",
              };
              await Promise.all([
                this.loadAutomationMessageDrafts(),
                this.loadAutomationQueue(),
                this.loadUnboundCommunications({ preserveSelection: true, forceReloadMessages: true, silent: true }),
              ]);
              return;
            }
            const errorText = String(response?.last_error_message || "").trim();
            if (messageStatus === "requires_manual_retry") {
              throw new Error(errorText || "Сообщение не отправлено автоматически и требует ручной обработки.");
            }
            if (messageStatus === "failed") {
              throw new Error(errorText || "Сообщение не удалось отправить.");
            }
            if (messageStatus === "queued" || messageStatus === "sending") {
              throw new Error("Сообщение поставлено в очередь, но ещё не подтверждено как отправленное.");
            }
            throw new Error("CRM не получила подтверждение успешной отправки сообщения.");
          } catch (error) {
            this.setUiError(`Ошибка отправки ответа: ${error.message}`, { modal: true });
          } finally {
            this.isManagerNotificationReplySending = false;
          }
        },
        async confirmAutomationDraft(draftId) {
          const normalizedDraftId = this.toIntOrNull(draftId);
          if (!normalizedDraftId) return;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.apiRequest(`/api/v1/automation-drafts/${normalizedDraftId}/confirm/`, {
              method: "POST",
              body: {},
            });
            await Promise.all([
              this.loadAutomationDrafts(),
              this.loadAutomationQueue(),
              this.loadAutomationMessageDrafts(),
              this.loadSection("touches"),
              this.loadSection("deals"),
              this.loadSection("companies"),
              this.loadSection("leads"),
            ]);
          } catch (error) {
            this.setUiError(`Ошибка подтверждения черновика: ${error.message}`, { modal: true });
          }
        },
        async dismissAutomationDraft(draftId) {
          const normalizedDraftId = this.toIntOrNull(draftId);
          if (!normalizedDraftId) return;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.apiRequest(`/api/v1/automation-drafts/${normalizedDraftId}/dismiss/`, {
              method: "POST",
              body: {},
            });
            await Promise.all([this.loadAutomationDrafts(), this.loadAutomationQueue(), this.loadAutomationMessageDrafts()]);
          } catch (error) {
            this.setUiError(`Ошибка отклонения черновика: ${error.message}`, { modal: true });
          }
        },
        async sendUnboundCommunicationMessage() {
          const conversation = this.activeUnboundConversation;
          if (!conversation?.id || this.isUnboundCommunicationSending) return;
          this.clearUiErrors({ modalOnly: true });
          this.isUnboundCommunicationSending = true;
          try {
            const response = await this.apiRequest(`/api/v1/communications/conversations/${conversation.id}/send/`, {
              method: "POST",
              body: {
                subject: this.unboundCommunicationComposer.subject,
                body_text: this.unboundCommunicationComposer.bodyText,
                recipient: this.unboundCommunicationComposer.recipient,
              }
            });
            this.ensureOutgoingMessageDelivered(response, "Письмо");
            this.unboundCommunicationComposer = this.getDefaultCommunicationComposer(conversation);
            await Promise.all([
              this.loadUnboundCommunications({ preserveSelection: true, forceReloadMessages: true, silent: true }),
              this.loadAutomationMessageDrafts(),
              this.loadAutomationQueue(),
            ]);
          } catch (error) {
            this.setUiError(`Ошибка отправки сообщения: ${error.message}`, { modal: true });
          } finally {
            this.isUnboundCommunicationSending = false;
          }
        },
        dealAutomationCardClass(item) {
          const priority = String(item?.uiPriority || "").trim();
          if (priority === "critical") {
            return "border-red-400/50 bg-red-400/10";
          }
          if (priority === "high") {
            return "border-amber-400/50 bg-amber-400/10";
          }
          if (priority === "medium") {
            return "border-sky-400/40 bg-sky-400/10";
          }
          return "border-crm-border/80 bg-[#0f2f4a]";
        },
        availableTouchResults(channelId, currentResultId = null) {
          if (this.showAllTouchResults) {
            return this.metaOptions.touchResults || [];
          }
          const normalizedChannelId = this.toIntOrNull(channelId);
          const currentId = this.toIntOrNull(currentResultId);
          const selectedLeadId = this.toIntOrNull(this.forms.touches.leadId);
          const selectedDealId = this.toIntOrNull(this.forms.touches.dealId);
          const selectedChannel = (this.metaOptions.communicationChannels || []).find(
            (channel) => String(channel.id) === String(normalizedChannelId || "")
          );
          const selectedChannelCode = this.normalizeTouchChannelCode(selectedChannel);
          const channelTouchResultIds = Array.isArray(selectedChannel?.touch_result_ids)
            ? selectedChannel.touch_result_ids.map((item) => this.toIntOrNull(item)).filter(Boolean)
            : [];
          const selectedLead = selectedLeadId
            ? (this.datasets.leads || []).find((lead) => String(lead.id) === String(selectedLeadId))
            : null;
          const selectedDeal = selectedDealId
            ? (this.datasets.deals || []).find((deal) => String(deal.id) === String(selectedDealId))
            : null;
          const selectedLeadStatus = this.toIntOrNull(selectedLead?.statusId)
            ? (this.metaOptions.leadStatuses || []).find((status) => String(status.id) === String(selectedLead.statusId))
            : null;
          const selectedDealStage = this.toIntOrNull(selectedDeal?.stageId)
            ? (this.metaOptions.dealStages || []).find((stage) => String(stage.id) === String(selectedDeal.stageId))
            : null;
          const leadTouchResultIds = Array.isArray(selectedLeadStatus?.touch_result_ids)
            ? selectedLeadStatus.touch_result_ids.map((item) => this.toIntOrNull(item)).filter(Boolean)
            : [];
          const dealTouchResultIds = Array.isArray(selectedDealStage?.touch_result_ids)
            ? selectedDealStage.touch_result_ids.map((item) => this.toIntOrNull(item)).filter(Boolean)
            : [];
          return (this.metaOptions.touchResults || []).filter((option) => {
            const allowedTypes = Array.isArray(option.allowed_touch_types) ? option.allowed_touch_types : [];
            const optionId = this.toIntOrNull(option.id);
            if (currentId && String(option.id) === String(currentId)) {
              return true;
            }
            if (normalizedChannelId && channelTouchResultIds.length) {
              if (!channelTouchResultIds.includes(optionId)) {
                return false;
              }
            } else if (allowedTypes.length && selectedChannelCode && !allowedTypes.includes(selectedChannelCode)) {
              return false;
            }
            if (selectedLeadId && leadTouchResultIds.length && !leadTouchResultIds.includes(optionId)) {
              return false;
            }
            if (selectedDealId && dealTouchResultIds.length && !dealTouchResultIds.includes(optionId)) {
              return false;
            }
            return true;
          });
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
        sortTasksByListRules(items) {
          const tasks = Array.isArray(items) ? items : [];
          const ordered = tasks.map((item, index) => ({ item, index }));
          ordered.sort((left, right) => {
            const leftActive = this.isTaskActiveStatus(left.item?.taskStatus);
            const rightActive = this.isTaskActiveStatus(right.item?.taskStatus);
            if (leftActive !== rightActive) {
              return leftActive ? -1 : 1;
            }
            if (leftActive && rightActive) {
              const taskOrder = this.compareActiveTasksByDueAt(left.item, right.item);
              if (taskOrder !== 0) {
                return taskOrder;
              }
            }
            return left.index - right.index;
          });
          return ordered.map((entry) => entry.item);
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
        resolveSingleFilterLabel(value, options, fallbackLabel = "", entityLabel = "Элемент") {
          const normalizedValue = String(value || "").trim();
          if (!normalizedValue) return "";
          const option = (Array.isArray(options) ? options : []).find(
            (item) => String(item?.value || "").trim() === normalizedValue
          );
          return String(option?.label || fallbackLabel || `${entityLabel} #${normalizedValue}`).trim();
        },
        resolveMultiFilterLabels(values, options, entityLabel = "Элемент") {
          const normalizedValues = Array.isArray(values)
            ? values.map((item) => String(item || "").trim()).filter(Boolean)
            : [];
          if (!normalizedValues.length) {
            return "";
          }
          const optionMap = new Map(
            (Array.isArray(options) ? options : []).map((item) => [String(item?.value || "").trim(), String(item?.label || "").trim()])
          );
          return normalizedValues.map((value) => optionMap.get(value) || `${entityLabel} #${value}`).join(", ");
        },
        clearActiveFilter(key) {
          if (key === "status") return this.clearStatusFilter();
          if (key === "deal_company") return this.clearDealCompanyFilter();
          if (key === "task_company") return this.clearTaskCompanyFilter();
          if (key === "task_category") return this.clearTaskCategoryFilter();
          if (key === "task_deal") return this.clearTaskDealFilter();
          if (key === "touch_company") return this.clearTouchCompanyFilter();
          if (key === "touch_deal") return this.clearTouchDealFilter();
        },
        statusFilterSections() {
          return ["leads", "deals", "contacts", "companies", "tasks", "touches"];
        },
        statsQuickFilterSections() {
          return ["leads", "deals", "companies", "tasks"];
        },
        syncStatusFiltersForSection(section) {
          const normalizedSection = String(section || "").trim();
          if (!this.statusFilterSections().includes(normalizedSection)) {
            return;
          }
          this.statusFiltersBySection = {
            ...this.statusFiltersBySection,
            [normalizedSection]: [...this.selectedStatusFilters],
          };
        },
        applyStatusFiltersForSection(section) {
          const normalizedSection = String(section || "").trim();
          const nextFilters = this.statusFilterSections().includes(normalizedSection)
            ? this.statusFiltersBySection?.[normalizedSection]
            : [];
          this.selectedStatusFilters = Array.isArray(nextFilters)
            ? nextFilters.map((item) => String(item || "").trim()).filter(Boolean)
            : [];
        },
        normalizeStatusFiltersBySection(payload) {
          const normalized = {};
          this.statusFilterSections().forEach((section) => {
            const rawValue = payload && Array.isArray(payload[section]) ? payload[section] : [];
            normalized[section] = rawValue.map((item) => String(item || "").trim()).filter(Boolean);
          });
          return normalized;
        },
        syncStatsQuickFilterForSection(section) {
          const normalizedSection = String(section || "").trim();
          if (!this.statsQuickFilterSections().includes(normalizedSection)) {
            return;
          }
          this.statsQuickFilterBySection = {
            ...this.statsQuickFilterBySection,
            [normalizedSection]: String(this.statsQuickFilterBySection?.[normalizedSection] || "").trim(),
          };
        },
        applyStatsQuickFilterForSection(section) {
          const normalizedSection = String(section || "").trim();
          if (!this.statsQuickFilterSections().includes(normalizedSection)) {
            return;
          }
          this.statsQuickFilterBySection = {
            ...this.statsQuickFilterBySection,
            [normalizedSection]: String(this.statsQuickFilterBySection?.[normalizedSection] || "").trim(),
          };
        },
        normalizeStatsQuickFilterBySection(payload) {
          const normalized = {};
          this.statsQuickFilterSections().forEach((section) => {
            normalized[section] = String(payload?.[section] || "").trim();
          });
          return normalized;
        },
        itemMatchesStatsQuickFilter(item, filterValue) {
          const normalizedFilter = String(filterValue || "").trim();
          if (!normalizedFilter) {
            return true;
          }
          if (this.activeSection === "companies") {
            if (normalizedFilter === "active") {
              return item?.isActive !== false;
            }
            if (normalizedFilter === "in_progress") {
              return this.companyHasActiveDeals(item?.id);
            }
            return true;
          }
          return this.getItemStatusBucket(item) === normalizedFilter;
        },
        isStatsQuickFilterActive(filterValue) {
          return String(this.activeStatsQuickFilter || "") === String(filterValue || "");
        },
        setStatsQuickFilter(filterValue = "") {
          const section = String(this.activeSection || "").trim();
          if (!this.statsQuickFilterSections().includes(section)) {
            return;
          }
          const normalizedValue = String(filterValue || "").trim();
          this.statsQuickFilterBySection = {
            ...this.statsQuickFilterBySection,
            [section]: normalizedValue,
          };
          this.persistFilters();
        },
        statsCardClass(filterValue = "") {
          return this.isStatsQuickFilterActive(filterValue)
            ? "border-crm-accent bg-crm-accent/12 shadow-[0_0_0_1px_rgba(96,165,250,0.18)_inset]"
            : "border-crm-border bg-crm-panel";
        },
        persistFilters() {
          this.syncStatusFiltersForSection(this.activeSection);
          this.syncStatsQuickFilterForSection(this.activeSection);
          try {
            window.localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify({
              statusFiltersBySection: this.statusFiltersBySection,
              statsQuickFilterBySection: this.statsQuickFilterBySection,
              dealCompanyFilterId: this.dealCompanyFilterId,
              dealCompanyFilterLabel: this.dealCompanyFilterLabel,
              selectedTaskCompanyFilters: this.selectedTaskCompanyFilters,
              selectedTaskCategoryFilters: this.selectedTaskCategoryFilters,
              taskDealFilterId: this.taskDealFilterId,
              taskDealFilterLabel: this.taskDealFilterLabel,
              selectedTouchCompanyFilters: this.selectedTouchCompanyFilters,
              touchDealFilterId: this.touchDealFilterId,
              touchDealFilterLabel: this.touchDealFilterLabel,
            }));
          } catch (error) {
          }
        },
        restoreFilters() {
          try {
            const rawValue = window.localStorage.getItem(FILTERS_STORAGE_KEY);
            if (!rawValue) return;
            const payload = JSON.parse(rawValue);
            const normalizedStatusFilters = this.normalizeStatusFiltersBySection(payload?.statusFiltersBySection);
            this.statsQuickFilterBySection = this.normalizeStatsQuickFilterBySection(payload?.statsQuickFilterBySection);
            if (Array.isArray(payload?.selectedStatusFilters)) {
              normalizedStatusFilters[this.activeSection] = payload.selectedStatusFilters
                .map((item) => String(item || "").trim())
                .filter(Boolean);
            }
            this.statusFiltersBySection = normalizedStatusFilters;
            this.applyStatusFiltersForSection(this.activeSection);
            this.applyStatsQuickFilterForSection(this.activeSection);
            this.dealCompanyFilterId = payload?.dealCompanyFilterId ? String(payload.dealCompanyFilterId).trim() : null;
            this.dealCompanyFilterLabel = String(payload?.dealCompanyFilterLabel || "").trim();
            this.selectedTaskCompanyFilters = Array.isArray(payload?.selectedTaskCompanyFilters)
              ? payload.selectedTaskCompanyFilters.map((item) => String(item || "").trim()).filter(Boolean)
              : [];
            this.selectedTaskCategoryFilters = Array.isArray(payload?.selectedTaskCategoryFilters)
              ? payload.selectedTaskCategoryFilters.map((item) => String(item || "").trim()).filter(Boolean)
              : [];
            this.taskDealFilterId = payload?.taskDealFilterId ? String(payload.taskDealFilterId).trim() : null;
            this.taskDealFilterLabel = String(payload?.taskDealFilterLabel || "").trim();
            this.selectedTouchCompanyFilters = Array.isArray(payload?.selectedTouchCompanyFilters)
              ? payload.selectedTouchCompanyFilters.map((item) => String(item || "").trim()).filter(Boolean)
              : [];
            this.touchDealFilterId = payload?.touchDealFilterId ? String(payload.touchDealFilterId).trim() : null;
            this.touchDealFilterLabel = String(payload?.touchDealFilterLabel || "").trim();
          } catch (error) {
          }
        },
        toggleStatusFilter() {
          this.showStatusFilter = !this.showStatusFilter;
          if (this.showStatusFilter) {
            this.showDealCompanyFilter = false;
            this.showTaskCompanyFilter = false;
            this.showTaskCategoryFilter = false;
            this.showTaskDealFilter = false;
            this.showTouchCompanyFilter = false;
            this.showTouchDealFilter = false;
          }
        },
        toggleStatusFilterValue(value) {
          if (this.selectedStatusFilters.includes(value)) {
            this.selectedStatusFilters = this.selectedStatusFilters.filter((item) => item !== value);
            this.persistFilters();
            return;
          }
          this.selectedStatusFilters = [...this.selectedStatusFilters, value];
          this.persistFilters();
        },
        clearStatusFilter() {
          this.selectedStatusFilters = [];
          this.persistFilters();
        },
        toggleDealCompanyFilter() {
          this.showDealCompanyFilter = !this.showDealCompanyFilter;
          if (this.showDealCompanyFilter) {
            this.showStatusFilter = false;
            this.showTaskCompanyFilter = false;
            this.showTaskCategoryFilter = false;
            this.showTaskDealFilter = false;
            this.showTouchCompanyFilter = false;
            this.showTouchDealFilter = false;
          }
        },
        setDealCompanyFilter(value, label = "") {
          this.dealCompanyFilterId = value ? String(value) : null;
          this.dealCompanyFilterLabel = String(label || "").trim();
          this.showDealCompanyFilter = false;
          this.persistFilters();
        },
        clearDealCompanyFilter() {
          this.dealCompanyFilterId = null;
          this.dealCompanyFilterLabel = "";
          this.persistFilters();
        },
        toggleTaskCompanyFilter() {
          this.showTaskCompanyFilter = !this.showTaskCompanyFilter;
          if (this.showTaskCompanyFilter) {
            this.showStatusFilter = false;
            this.showDealCompanyFilter = false;
            this.showTaskCategoryFilter = false;
            this.showTaskDealFilter = false;
            this.showTouchCompanyFilter = false;
            this.showTouchDealFilter = false;
          }
        },
        toggleTaskCompanyFilterValue(value) {
          const normalizedValue = String(value || "");
          if (this.selectedTaskCompanyFilters.includes(normalizedValue)) {
            this.selectedTaskCompanyFilters = this.selectedTaskCompanyFilters.filter((item) => item !== normalizedValue);
            this.persistFilters();
            return;
          }
          this.selectedTaskCompanyFilters = [...this.selectedTaskCompanyFilters, normalizedValue];
          this.persistFilters();
        },
        clearTaskCompanyFilter() {
          this.selectedTaskCompanyFilters = [];
          this.persistFilters();
        },
        toggleTaskCategoryFilter() {
          this.showTaskCategoryFilter = !this.showTaskCategoryFilter;
          if (this.showTaskCategoryFilter) {
            this.showStatusFilter = false;
            this.showDealCompanyFilter = false;
            this.showTaskCompanyFilter = false;
            this.showTaskDealFilter = false;
            this.showTouchCompanyFilter = false;
            this.showTouchDealFilter = false;
          }
        },
        toggleTaskCategoryFilterValue(value) {
          const normalizedValue = String(value || "");
          if (this.selectedTaskCategoryFilters.includes(normalizedValue)) {
            this.selectedTaskCategoryFilters = this.selectedTaskCategoryFilters.filter((item) => item !== normalizedValue);
            this.persistFilters();
            return;
          }
          this.selectedTaskCategoryFilters = [...this.selectedTaskCategoryFilters, normalizedValue];
          this.persistFilters();
        },
        clearTaskCategoryFilter() {
          this.selectedTaskCategoryFilters = [];
          this.persistFilters();
        },
        toggleTaskDealFilter() {
          this.showTaskDealFilter = !this.showTaskDealFilter;
          if (this.showTaskDealFilter) {
            this.showStatusFilter = false;
            this.showDealCompanyFilter = false;
            this.showTaskCompanyFilter = false;
            this.showTaskCategoryFilter = false;
            this.showTouchCompanyFilter = false;
            this.showTouchDealFilter = false;
          }
        },
        setTaskDealFilter(value, label = "") {
          this.taskDealFilterId = value ? String(value) : null;
          this.taskDealFilterLabel = String(label || "").trim();
          this.showTaskDealFilter = false;
          this.persistFilters();
        },
        toggleTouchCompanyFilter() {
          this.showTouchCompanyFilter = !this.showTouchCompanyFilter;
          if (this.showTouchCompanyFilter) {
            this.showStatusFilter = false;
            this.showDealCompanyFilter = false;
            this.showTaskCompanyFilter = false;
            this.showTaskDealFilter = false;
            this.showTouchDealFilter = false;
          }
        },
        toggleTouchCompanyFilterValue(value) {
          const normalizedValue = String(value || "");
          if (this.selectedTouchCompanyFilters.includes(normalizedValue)) {
            this.selectedTouchCompanyFilters = this.selectedTouchCompanyFilters.filter((item) => item !== normalizedValue);
            this.persistFilters();
            return;
          }
          this.selectedTouchCompanyFilters = [...this.selectedTouchCompanyFilters, normalizedValue];
          this.persistFilters();
        },
        clearTouchCompanyFilter() {
          this.selectedTouchCompanyFilters = [];
          this.persistFilters();
        },
        toggleTouchDealFilter() {
          this.showTouchDealFilter = !this.showTouchDealFilter;
          if (this.showTouchDealFilter) {
            this.showStatusFilter = false;
            this.showDealCompanyFilter = false;
            this.showTaskCompanyFilter = false;
            this.showTaskDealFilter = false;
            this.showTouchCompanyFilter = false;
          }
        },
        setTouchDealFilter(value, label = "") {
          this.touchDealFilterId = value ? String(value) : null;
          this.touchDealFilterLabel = String(label || "").trim();
          this.showTouchDealFilter = false;
          this.persistFilters();
        },
        clearTouchDealFilter() {
          this.touchDealFilterId = null;
          this.touchDealFilterLabel = "";
          this.persistFilters();
        },
        clearTaskDealFilter() {
          this.taskDealFilterId = null;
          this.taskDealFilterLabel = "";
          this.persistFilters();
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
          if (event.key === "Escape") {
            if (this.showManagerNotifications) {
              event.preventDefault();
              this.showManagerNotifications = false;
              return;
            }
            if (!this.showModal) return;
            event.preventDefault();
            this.closeModal();
            return;
          }

          if (!this.showModal) return;

          if (event.key !== "Enter" || event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) {
            return;
          }

          const target = event.target;
          const tagName = String((target && target.tagName) || "").toUpperCase();
          if (tagName === "TEXTAREA") {
            return;
          }

          event.preventDefault();
          if (this.isSaving) {
            return;
          }
          await this.createItem();
        },
        handleDocumentClick(event) {
          const target = event.target;
          if (this.showManagerNotifications) {
            if (target && target.closest && target.closest("[data-manager-notifications]")) return;
            this.showManagerNotifications = false;
          }
          if (this.showStatusFilter) {
            if (target && target.closest && target.closest("[data-status-filter]")) return;
            this.showStatusFilter = false;
          }
          if (this.showDealCompanyFilter) {
            if (target && target.closest && target.closest("[data-deal-company-filter]")) return;
            this.showDealCompanyFilter = false;
          }
          if (this.showTaskCompanyFilter) {
            if (target && target.closest && target.closest("[data-task-company-filter]")) return;
            this.showTaskCompanyFilter = false;
          }
          if (this.showTaskCategoryFilter) {
            if (target && target.closest && target.closest("[data-task-category-filter]")) return;
            this.showTaskCategoryFilter = false;
          }
          if (this.showTaskDealFilter) {
            if (target && target.closest && target.closest("[data-task-deal-filter]")) return;
            this.showTaskDealFilter = false;
          }
          if (this.showTouchCompanyFilter) {
            if (target && target.closest && target.closest("[data-touch-company-filter]")) return;
            this.showTouchCompanyFilter = false;
          }
          if (this.showTouchDealFilter) {
            if (target && target.closest && target.closest("[data-touch-deal-filter]")) return;
            this.showTouchDealFilter = false;
          }
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
          this.leadSummaryEditingField = "";
          this.taskSummaryEditingField = "";
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingDealId = null;
          this.resetExpandedOptionalFields();
          this.editingLeadId = item.id;
          this.showLeadDocumentsPanel = false;
          this.showLeadPhoneCallHistory = false;
          this.leadDocumentsForActiveLead = [];
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
            websiteSessionId: item.websiteSessionId || "",
            events: item.events || ""
          };
          this.showModal = true;
        },
        openDealEditor(item) {
          this.clearUiErrors({ modalOnly: true });
          this.taskSummaryEditingField = "";
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingLeadId = null;
          this.resetExpandedOptionalFields();
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
          this.resetDealCommunicationsState();
          this.showDealDocumentsPanel = false;
          this.resetDealDocumentGeneratorState();
          this.showDealPhoneCallHistory = false;
          this.dealDocumentsForActiveDeal = [];
          this.resetDealCompanyForm();
          this.showDealCompanyForm = false;
          this.showDealContactsPanel = false;
          this.showDealContactForm = false;
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          if (this.forms.deals.companyId) {
            this.loadContactsForSelectedDealCompany();
          }
          this.loadTasksForDeal();
          this.showModal = true;
        },
        async openDealEditorById(dealId) {
          const normalizedId = this.toIntOrNull(dealId);
          if (!normalizedId) return;
          try {
            const deal = await this.fetchDealById(normalizedId);
            this.openDealEditor(deal);
          } catch (error) {
            this.errorMessage = `Ошибка открытия сделки: ${error.message}`;
          }
        },
        async openLeadEditorById(leadId) {
          const normalizedId = this.toIntOrNull(leadId);
          if (!normalizedId) return;
          try {
            const lead = await this.fetchLeadById(normalizedId);
            this.openLeadEditor(lead);
          } catch (error) {
            this.errorMessage = `Ошибка открытия лида: ${error.message}`;
          }
        },
        async openCompanyEditorById(companyId, options = {}) {
          const normalizedId = this.toIntOrNull(companyId);
          if (!normalizedId) return;
          try {
            const company = await this.fetchCompanyById(normalizedId);
            this.openCompanyEditor(company, options);
          } catch (error) {
            this.errorMessage = `Ошибка открытия компании: ${error.message}`;
          }
        },
        openContactEditor(item) {
          this.clearUiErrors({ modalOnly: true });
          this.activeSection = "contacts";
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
            telegram: item.telegram || "",
            whatsapp: item.whatsapp || "",
            maxContact: item.maxContact || "",
            roleId: this.toIntOrNull(item.roleId),
            role: item.role || "",
            personNote: item.personNote || "",
            isPrimary: !!item.isPrimary
          };
          this.showModal = true;
          this.ensurePhoneCallHistoryLoaded("contact", this.editingContactId).catch(() => {});
        },
        openCompanyEditor(item, options = {}) {
          this.clearUiErrors({ modalOnly: true });
          this.activeSection = "companies";
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingCompanyId = item.id;
          this.companySummaryEditingField = "";
          this.showCompanyEvents = false;
          this.showCompanyRequisites = false;
          this.showCompanyWorkRules = false;
          this.showCompanyContactsPanel = false;
          this.showCompanyDocumentsPanel = false;
          this.showCompanySettlementsPanel = false;
          this.showCompanyPhoneCallHistory = false;
          this.resetCompanyCommunicationsState();
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyNoteDraft = false;
          this.companyDocumentsForActiveCompany = [];
          this.companyDealDocumentGroups = [];
          this.resetCompanySettlementState();
          this.resetExpandedOptionalFields();
          const normalizedOkveds = this.normalizeCompanyOkveds(item.okveds, item.okved, item.industry);
          const resolvedIndustry = this.resolvePrimaryIndustry(item.industry, item.okved, normalizedOkveds);
          this.forms.companies = {
            name: item.name || "",
            legalName: item.legalName || "",
            inn: item.inn || "",
            companyType: item.companyType || "client",
            address: item.address || "",
            actualAddress: item.actualAddress || "",
            ogrn: item.ogrn || "",
            kpp: item.kpp || "",
            bankDetails: item.bankDetails || "",
            settlementAccount: item.settlementAccount || "",
            correspondentAccount: item.correspondentAccount || "",
            iban: item.iban || "",
            bik: item.bik || "",
            bankName: item.bankName || "",
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
          this.showCompanyContactsPanel = false;
          this.showCompanyDocumentsPanel = false;
          this.showCompanySettlementsPanel = false;
          this.showCompanyPhoneCallHistory = false;
          this.resetCompanyCommunicationsState();
          this.showCompanyWorkRules = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.resetCompanySettlementContractForm();
          this.resetCompanySettlementDocumentForm();
          this.resetCompanySettlementAllocationForm();
          this.loadContactsForCompany();
          this.showModal = true;
          this.enrichCompanyFromDadataByInn();
          if (String(options.openPanel || "").trim() === "settlements") {
            this.$nextTick(() => {
              this.toggleCompanySettlementsPanel().catch((error) => {
                this.errorMessage = `Ошибка загрузки взаиморасчетов: ${error.message}`;
              });
            });
          }
        },
        openTaskEditor(item, options = {}) {
          if (Object.prototype.hasOwnProperty.call(options, "parentContext")) {
            this.modalParentContext = options.parentContext;
          }
          this.clearUiErrors({ modalOnly: true });
          this.activeSection = "tasks";
          this.taskSummaryEditingField = "";
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.resetExpandedOptionalFields();
          this.editingTaskId = item.id;
          this.forms.tasks = {
            subject: item.subject || item.name || "",
            taskCategoryId: this.toIntOrNull(item.taskTypeCategoryId || this.resolveTaskTypeCategoryIdById(item.taskTypeId)),
            taskTypeId: this.toIntOrNull(item.taskTypeId),
            communicationChannelId: this.toIntOrNull(item.communicationChannelId),
            priority: item.priority || "medium",
            ownerId: this.toIntOrNull(item.ownerId) || this.currentUserId,
            companyId: this.toIntOrNull(item.clientId),
            leadId: this.toIntOrNull(item.leadId),
            dealId: this.toIntOrNull(item.dealId),
            relatedTouchId: this.toIntOrNull(item.relatedTouchId),
            dueAt: this.toDateTimeLocal(item.dueAtRaw),
            reminderOffsetMinutes: Number(item.reminderOffsetMinutes || 30),
            checklist: this.normalizeTaskChecklist(item.checklist),
            description: item.description || "",
            result: item.result || this.resolveTaskTypeDefaultResultById(item.taskTypeId),
            saveCompanyNote: !!item.saveCompanyNote,
            companyNote: item.companyNote || "",
            status: item.taskStatus || item.status || "todo"
          };
          this.taskChecklistHideCompleted = false;
          this.resetTaskFollowUpForm();
          this.showModal = true;
          this.loadTaskTouchOptions();
        },
        cloneModalContextValue(value) {
          if (value === undefined) return undefined;
          return JSON.parse(JSON.stringify(value));
        },
        captureModalParentContext() {
          if (!this.showModal) {
            return null;
          }
          if (this.activeSection === "deals" && this.toIntOrNull(this.editingDealId)) {
            return {
              section: "deals",
              editingDealId: this.toIntOrNull(this.editingDealId),
              dealSummaryEditingField: String(this.dealSummaryEditingField || ""),
              showDealTaskForm: !!this.showDealTaskForm,
              dealTaskForm: this.cloneModalContextValue(this.dealTaskForm),
              showDealCompanyForm: !!this.showDealCompanyForm,
              dealCompanyForm: this.cloneModalContextValue(this.dealCompanyForm),
              showDealContactsPanel: !!this.showDealContactsPanel,
              showDealDocumentsPanel: !!this.showDealDocumentsPanel,
              showDealCommunicationsPanel: !!this.showDealCommunicationsPanel,
              showDealPhoneCallHistory: !!this.showDealPhoneCallHistory,
              showDealContactForm: !!this.showDealContactForm,
            };
          }
          if (this.activeSection === "leads" && this.toIntOrNull(this.editingLeadId)) {
            return {
              section: "leads",
              editingLeadId: this.toIntOrNull(this.editingLeadId),
              leadSummaryEditingField: String(this.leadSummaryEditingField || ""),
              showLeadDocumentsPanel: !!this.showLeadDocumentsPanel,
              showLeadPhoneCallHistory: !!this.showLeadPhoneCallHistory,
            };
          }
          return null;
        },
        async restoreModalParentContext() {
          const context = this.modalParentContext;
          this.modalParentContext = null;
          if (!context) {
            return false;
          }
          this.clearUiErrors({ modalOnly: true });
          this.setTouchResultPrompt("");
          this.showAllTouchResults = false;
          this.activeSection = context.section;
          this.showModal = true;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.touchDealDocuments = [];
          this.touchCompanyDocuments = [];
          this.resetTouchFollowUpForm();
          this.resetTaskFollowUpForm();
          this.taskTouchOptions = [];
          if (context.section === "deals") {
            this.editingLeadId = null;
            this.editingDealId = this.toIntOrNull(context.editingDealId);
            this.dealSummaryEditingField = String(context.dealSummaryEditingField || "");
            this.showDealTaskForm = !!context.showDealTaskForm;
            this.dealTaskForm = this.cloneModalContextValue(context.dealTaskForm) || this.dealTaskForm;
            this.showDealCompanyForm = !!context.showDealCompanyForm;
            this.dealCompanyForm = this.cloneModalContextValue(context.dealCompanyForm) || this.dealCompanyForm;
            this.showDealContactsPanel = !!context.showDealContactsPanel;
            this.showDealDocumentsPanel = !!context.showDealDocumentsPanel;
            this.showDealCommunicationsPanel = !!context.showDealCommunicationsPanel;
            this.showDealPhoneCallHistory = !!context.showDealPhoneCallHistory;
            this.showDealContactForm = !!context.showDealContactForm;
            await this.loadTasksForDeal();
            if (this.toIntOrNull(this.forms.deals.companyId)) {
              await this.loadContactsForSelectedDealCompany();
            }
            if (this.showDealDocumentsPanel) {
              await this.loadDealDocuments();
            }
            if (this.showDealCommunicationsPanel) {
              await this.loadDealCommunications();
            }
            if (this.showDealPhoneCallHistory) {
              await this.ensurePhoneCallHistoryLoaded("deal", this.editingDealId);
            }
            return true;
          }
          if (context.section === "leads") {
            this.editingDealId = null;
            this.editingLeadId = this.toIntOrNull(context.editingLeadId);
            this.leadSummaryEditingField = String(context.leadSummaryEditingField || "");
            this.showLeadDocumentsPanel = !!context.showLeadDocumentsPanel;
            this.showLeadPhoneCallHistory = !!context.showLeadPhoneCallHistory;
            if (this.showLeadDocumentsPanel) {
              await this.loadLeadDocuments();
            }
            if (this.showLeadPhoneCallHistory) {
              await this.ensurePhoneCallHistoryLoaded("lead", this.editingLeadId);
            }
            return true;
          }
          return false;
        },
        openTouchEditor(item, options = {}) {
          if (Object.prototype.hasOwnProperty.call(options, "parentContext")) {
            this.modalParentContext = options.parentContext;
          }
          this.clearUiErrors({ modalOnly: true });
          this.setTouchResultPrompt("");
          this.showAllTouchResults = false;
          this.activeSection = "touches";
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.editingTouchId = item.id;
          const resolvedOwnerId = this.toIntOrNull(item.ownerId) || this.resolveTouchOwnerIdFromContext({
            dealId: this.toIntOrNull(item.dealId),
            leadId: this.toIntOrNull(item.leadId),
            taskId: this.toIntOrNull(item.taskId),
            companyId: this.toIntOrNull(item.clientId),
          });
          this.forms.touches = {
            happenedAt: this.toDateTimeLocal(item.happenedAtRaw),
            channelId: this.toIntOrNull(item.channelId),
            resultOptionId: this.toIntOrNull(item.resultOptionId),
            direction: item.direction || "outgoing",
            summary: item.summary || "",
            nextStep: item.nextStep || "",
            nextStepAt: this.toDateTimeLocal(item.nextStepAtRaw),
            ownerId: resolvedOwnerId,
            companyId: this.toIntOrNull(item.clientId),
            contactId: this.toIntOrNull(item.contactId),
            taskId: this.toIntOrNull(item.taskId),
            leadId: this.toIntOrNull(item.leadId),
            dealId: this.toIntOrNull(item.dealId),
            dealDocumentIds: (item.dealDocuments || []).map((document) => this.toIntOrNull(document.id)).filter(Boolean),
            clientDocumentIds: (item.clientDocuments || []).map((document) => this.toIntOrNull(document.id)).filter(Boolean),
            documentUploadTarget: this.toIntOrNull(item.dealId) ? "deal" : (this.toIntOrNull(item.clientId) ? "company" : ""),
          };
          this.resetTouchFollowUpForm();
          this.loadTouchDocuments();
          this.showModal = true;
          this.$nextTick(() => this.applyTouchAutomationRule());
        },
        openTaskFromDeal(task) {
          this.taskDealFilterId = task.dealId || this.editingDealId || null;
          this.taskDealFilterLabel = task.deal || this.forms.deals.title || "";
          this.persistFilters();
          this.openTaskEditor(task, { parentContext: this.modalParentContext || this.captureModalParentContext() });
        },
        async openTaskListForDeal() {
          if (!this.editingDealId) return;
          this.taskDealFilterId = this.editingDealId;
          this.taskDealFilterLabel = this.forms.deals.title || `Сделка #${this.editingDealId}`;
          this.closeModal();
          this.activeSection = "tasks";
          this.search = "";
          this.showStatusFilter = false;
          this.showTaskCompanyFilter = false;
          this.showTaskCategoryFilter = false;
          this.showTaskDealFilter = false;
          this.showTouchCompanyFilter = false;
          this.showTouchDealFilter = false;
          this.selectedStatusFilters = [];
          this.selectedTaskCompanyFilters = [];
          this.selectedTaskCategoryFilters = [];
          this.selectedTouchCompanyFilters = [];
          this.clearTouchDealFilter();
          this.persistFilters();
          if (!this.datasets.tasks.length) {
            await this.reloadActiveSection();
          }
        },
        toggleDealTaskForm() {
          this.showDealTaskForm = !this.showDealTaskForm;
          if (this.showDealTaskForm) {
            this.showDealDocumentsPanel = false;
            this.showDealContactsPanel = false;
            this.showDealCommunicationsPanel = false;
            this.showDealPhoneCallHistory = false;
            this.stopCommunicationsPollingIfIdle();
          }
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
            this.showDealDocumentsPanel = false;
            this.showDealTaskForm = false;
            this.showDealCommunicationsPanel = false;
            this.showDealPhoneCallHistory = false;
            this.stopCommunicationsPollingIfIdle();
            await this.loadContactsForSelectedDealCompany();
            this.scrollPanelIntoView("deal-contacts-panel");
            return;
          }
          this.showDealContactForm = false;
        },
        async toggleDealCommunicationsPanel() {
          if (!this.editingDealId) return;
          this.showDealCommunicationsPanel = !this.showDealCommunicationsPanel;
          if (this.showDealCommunicationsPanel) {
            this.showDealDocumentsPanel = false;
            this.showDealContactsPanel = false;
            this.showDealTaskForm = false;
            this.showDealPhoneCallHistory = false;
            await this.loadDealCommunications({ preserveSelection: false });
            this.scrollPanelIntoView("deal-communications-panel");
            return;
          }
          this.stopCommunicationsPollingIfIdle();
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
            taskCategoryId: null,
            taskTypeId: null,
            communicationChannelId: null,
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          };
        },
        resetTouchFollowUpForm() {
          this.touchFollowUpForm = {
            subject: "",
            taskCategoryId: null,
            taskTypeId: null,
            communicationChannelId: null,
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          };
        },
        resetTaskFollowUpForm() {
          this.taskFollowUpForm = {
            subject: "",
            taskCategoryId: null,
            taskTypeId: null,
            communicationChannelId: null,
            dueAt: "",
            reminderOffsetMinutes: 30,
            description: ""
          };
        },
        createTaskChecklistItem(overrides = {}) {
          return {
            id: String(overrides.id || `checklist-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`),
            text: String(overrides.text || "").trim(),
            isDone: !!(overrides.isDone ?? overrides.is_done),
          };
        },
        normalizeTaskChecklist(items) {
          return (Array.isArray(items) ? items : [])
            .filter((item) => item && typeof item === "object")
            .map((item) => this.createTaskChecklistItem(item));
        },
        serializeTaskChecklist(items) {
          return this.normalizeTaskChecklist(items)
            .map((item) => ({
              id: item.id,
              text: String(item.text || "").trim(),
              is_done: !!item.isDone,
            }))
            .filter((item) => item.text);
        },
        ensureTaskChecklistVisible() {
          if (!this.expandedOptionalFields.tasks) {
            this.expandedOptionalFields.tasks = {};
          }
          this.expandedOptionalFields.tasks = {
            ...this.expandedOptionalFields.tasks,
            checklist: true,
          };
        },
        createTaskChecklist() {
          this.ensureTaskChecklistVisible();
          if (!this.normalizeTaskChecklist(this.forms.tasks.checklist).length) {
            this.forms.tasks.checklist = [this.createTaskChecklistItem()];
          }
        },
        addTaskChecklistItem() {
          const nextChecklist = this.normalizeTaskChecklist(this.forms.tasks.checklist);
          nextChecklist.push(this.createTaskChecklistItem());
          this.forms.tasks.checklist = nextChecklist;
          this.ensureTaskChecklistVisible();
        },
        removeTaskChecklistItem(index) {
          this.forms.tasks.checklist = this.normalizeTaskChecklist(this.forms.tasks.checklist)
            .filter((item, itemIndex) => itemIndex !== index);
        },
        visibleTaskChecklist() {
          return this.normalizeTaskChecklist(this.forms.tasks.checklist)
            .map((item, index) => ({
              ...item,
              originalIndex: index,
            }))
            .filter((item) => !(this.taskChecklistHideCompleted && item.isDone));
        },
        hasTaskChecklist() {
          return this.normalizeTaskChecklist(this.forms.tasks.checklist).length > 0;
        },
        hasHiddenCompletedTaskChecklistItems() {
          return this.taskChecklistHideCompleted
            && this.normalizeTaskChecklist(this.forms.tasks.checklist).some((item) => item.isDone)
            && !this.visibleTaskChecklist().length;
        },
        hasPreparedTouchFollowUp() {
          return !!(
            this.touchFollowUpForm.subject.trim()
            || this.touchFollowUpForm.taskCategoryId
            || this.touchFollowUpForm.taskTypeId
            || this.touchFollowUpForm.communicationChannelId
            || this.touchFollowUpForm.dueAt
            || this.touchFollowUpForm.description.trim()
          );
        },
        hasValidTouchFollowUp() {
          return !!(this.resolveTaskSubject(this.touchFollowUpForm) && this.touchFollowUpForm.dueAt);
        },
        hasPendingDealTaskDraft() {
          return !!(
            this.dealTaskForm.subject.trim()
            || this.dealTaskForm.taskCategoryId
            || this.dealTaskForm.taskTypeId
            || this.dealTaskForm.communicationChannelId
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
          if (!this.resolveTaskSubject(this.dealTaskForm)) {
            throw new Error("Укажите название новой задачи по сделке или выберите тип задачи");
          }
          if (!this.dealTaskForm.dueAt) {
            throw new Error("Укажите срок новой задачи по сделке");
          }
        },
        hasPreparedTaskFollowUp() {
          return !!(
            this.resolveTaskSubject(this.taskFollowUpForm)
            && this.taskFollowUpForm.dueAt
          );
        },
        resolveTaskSubject(formLike) {
          const form = formLike && typeof formLike === "object" ? formLike : {};
          const explicitSubject = String(form.subject || "").trim();
          if (explicitSubject) {
            return explicitSubject;
          }
          const taskTypeId = this.toIntOrNull(form.taskTypeId);
          if (!taskTypeId) {
            return "";
          }
          const taskType = (this.metaOptions.taskTypes || []).find((item) => String(item.id) === String(taskTypeId));
          return String(taskType?.name || "").trim();
        },
        validateTaskFollowUpRequirement() {
          if (!this.isTaskDoneStatus(this.forms.tasks.status)) {
            return;
          }
          const dealId = String(this.toIntOrNull(this.forms.tasks.dealId) || "");
          const hasOtherActiveTask = Array.isArray(this.datasets.tasks)
            && this.datasets.tasks.some((task) => (
              String(task.id) !== String(this.editingTaskId)
              && String(task.dealId || "") === dealId
              && this.isTaskActiveStatus(task.taskStatus)
            ));
          if (this.currentTaskTypeHasAutomaticFollowUp) {
            return;
          }
          if (this.taskFormRequiresFollowUp(this.forms.tasks)) {
            if (this.hasPreparedTaskFollowUp() || hasOtherActiveTask) {
              return;
            }
            throw new Error("Для внутренней задачи заполните следующую задачу перед завершением текущей");
          }
          if (!this.taskActiveDealRequiresFollowUp) {
            return;
          }
          if (hasOtherActiveTask || this.hasPreparedTaskFollowUp()) {
            return;
          }
          throw new Error("Для активной сделки заполните следующую задачу или держите другую активную задачу");
        },
        validateTaskCompletionEvidence(form) {
          if (!this.isTaskDoneStatus(form.status)) {
            return;
          }
          const hasResult = !!this.resolveTaskResultValue(form);
          if (this.taskFormUsesCommunicationChannel(form)) {
            if (!this.toIntOrNull(form.communicationChannelId)) {
              throw new Error("Укажите тип канала перед завершением клиентской задачи");
            }
          }
          if (!hasResult) {
            throw new Error("Укажите результат выполнения задачи или задайте его в типе задачи");
          }
        },
        resetDealCompanyForm() {
          this.dealCompanyForm = {
            name: "",
            inn: "",
            companyType: "client",
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
        formatDealAmountSummary(amount, currency) {
          const numeric = Number(amount);
          if (!Number.isFinite(numeric) || numeric <= 0) {
            return "Не указана";
          }
          return `${numeric.toLocaleString("ru-RU")} ${String(currency || "RUB").trim()}`;
        },
        isDealSummaryEditing(fieldKey) {
          return String(this.dealSummaryEditingField || "") === String(fieldKey || "");
        },
        startDealSummaryEdit(fieldKey) {
          this.dealSummaryEditingField = String(fieldKey || "");
        },
        stopDealSummaryEdit(fieldKey = "") {
          if (!fieldKey || this.isDealSummaryEditing(fieldKey)) {
            this.dealSummaryEditingField = "";
          }
        },
        openDealSummaryField(fieldKey) {
          if (fieldKey === "contact") {
            if (!this.toIntOrNull(this.forms.deals.companyId)) {
              this.startDealSummaryEdit("companyId");
              return;
            }
            this.showDealContactsPanel = true;
            return;
          }
          if (fieldKey === "touch") {
            const parentContext = this.captureModalParentContext();
            const touch = this.dealSummaryNextTouch || this.dealSummaryLastTouch;
            if (touch) {
              this.openTouchEditor(touch, { parentContext });
              return;
            }
            this.modalParentContext = parentContext;
            this.activeSection = "touches";
            this.editingTouchId = null;
            this.forms.touches = {
              ...this.getDefaultForm("touches"),
              happenedAt: this.toDateTimeLocal(new Date().toISOString()),
              companyId: this.toIntOrNull(this.forms.deals.companyId),
              dealId: this.toIntOrNull(this.editingDealId),
              ownerId: this.resolveTouchOwnerIdFromContext({
                dealId: this.editingDealId,
                companyId: this.forms.deals.companyId,
              }),
              documentUploadTarget: this.toIntOrNull(this.editingDealId) ? "deal" : (this.toIntOrNull(this.forms.deals.companyId) ? "company" : ""),
            };
            this.loadTouchDocuments();
            this.showModal = true;
            return;
          }
          if (fieldKey === "nextStep") {
            const parentContext = this.captureModalParentContext();
            if (this.dealSummaryNextStepTask) {
              this.openTaskEditor(this.dealSummaryNextStepTask, { parentContext });
              return;
            }
            const touch = this.dealSummaryNextTouch || this.dealSummaryLastTouch;
            if (touch) {
              this.openTouchEditor(touch, { parentContext });
              return;
            }
            return;
          }
          this.startDealSummaryEdit(fieldKey);
        },
        quickAddDealTouch() {
          this.modalParentContext = this.captureModalParentContext();
          this.activeSection = "touches";
          this.editingTouchId = null;
          this.showAllTouchResults = false;
          this.forms.touches = {
            ...this.getDefaultForm("touches"),
            happenedAt: this.toDateTimeLocal(new Date().toISOString()),
            companyId: this.toIntOrNull(this.forms.deals.companyId),
            dealId: this.toIntOrNull(this.editingDealId),
            ownerId: this.resolveTouchOwnerIdFromContext({
              dealId: this.editingDealId,
              companyId: this.forms.deals.companyId,
            }),
            documentUploadTarget: this.toIntOrNull(this.editingDealId) ? "deal" : (this.toIntOrNull(this.forms.deals.companyId) ? "company" : ""),
          };
          this.loadTouchDocuments();
          this.showModal = true;
          this.$nextTick(() => this.applyTouchAutomationRule());
        },
        quickToggleDealTaskForm() {
          this.showDealTaskForm = true;
          this.showDealPhoneCallHistory = false;
          this.showDealDocumentsPanel = false;
          this.showDealContactsPanel = false;
          this.showDealCommunicationsPanel = false;
          this.stopCommunicationsPollingIfIdle();
          this.$nextTick(() => {
            const panel = document.getElementById("deal-task-panel");
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
        },
        scrollToDealTasksPanel() {
          this.$nextTick(() => {
            const panel = document.getElementById("deal-task-panel");
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
        },
        prepareDealTaskFromAutomation(item) {
          if (!item) return;
          this.showDealTaskForm = true;
          this.showDealPhoneCallHistory = false;
          this.showDealDocumentsPanel = false;
          this.showDealContactsPanel = false;
          this.showDealCommunicationsPanel = false;
          this.stopCommunicationsPollingIfIdle();
          this.resetDealTaskForm();
          this.dealTaskForm.subject = String(item.title || item.recommendedAction || "").trim();
          this.dealTaskForm.taskCategoryId = this.toIntOrNull(item.taskCategoryId || item.defaultTaskCategoryId);
          this.dealTaskForm.communicationChannelId = this.toIntOrNull(item.communicationChannelId);
          const dueAt = item.at || item.suggestedNextStepAt || item.nextStepAtRaw || "";
          this.dealTaskForm.dueAt = dueAt ? this.toDateTimeLocal(dueAt) : "";
          this.$nextTick(() => {
            const panel = document.getElementById("deal-task-panel");
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
        },
        quickOpenDealDocuments() {
          this.toggleDealDocumentsPanel();
        },
        async openDealCompanySettlements() {
          const companyId = this.toIntOrNull(this.forms.deals.companyId) || this.toIntOrNull(this.editingDealItem?.clientId);
          if (!companyId) {
            this.setUiError("У сделки не выбрана компания.", { modal: true });
            return;
          }
          await this.openCompanyEditorById(companyId, { openPanel: "settlements" });
        },
        formatFileSize(bytes) {
          const size = Number.parseInt(bytes, 10);
          if (!Number.isFinite(size) || size <= 0) return "0 Б";
          if (size < 1024) return `${size} Б`;
          if (size < 1024 * 1024) return `${(size / 1024).toFixed(1).replace(".0", "")} КБ`;
          return `${(size / (1024 * 1024)).toFixed(1).replace(".0", "")} МБ`;
        },
        preferredOwnCompanyId() {
          const preferred = Array.isArray(this.ownCompanyOptions) && this.ownCompanyOptions.length
            ? this.ownCompanyOptions[0]
            : null;
          return this.toIntOrNull(preferred?.id);
        },
        dealDocumentGeneratorCompanyId() {
          return this.toIntOrNull(this.forms.deals.companyId) || this.toIntOrNull(this.editingDealItem?.clientId);
        },
        preferredDealDocumentGeneratorContractId() {
          const activeContract = (this.dealDocumentGeneratorContracts || []).find((contract) => contract.isActive !== false);
          return this.toIntOrNull(activeContract?.id || this.dealDocumentGeneratorContracts[0]?.id);
        },
        defaultDealActLineDescription() {
          return String(this.forms.deals.title || this.editingDealItem?.title || "").trim() || "Услуги по сделке";
        },
        defaultDealActLineQuantity(rateOverride = null) {
          const hourlyRate = Number(rateOverride ?? this.selectedDealDocumentGeneratorHourlyRate ?? 0);
          const amount = this.parseFlexibleNumber(this.forms.deals.amount || this.editingDealItem?.amount);
          if (hourlyRate > 0 && amount > 0) {
            return (amount / hourlyRate).toFixed(2);
          }
          return "1";
        },
        defaultDealActLinePrice() {
          const hourlyRate = Number(this.selectedDealDocumentGeneratorHourlyRate || 0);
          if (hourlyRate > 0) {
            return hourlyRate.toFixed(2);
          }
          const amount = this.parseFlexibleNumber(this.forms.deals.amount || this.editingDealItem?.amount);
          return amount > 0 ? amount.toFixed(2) : "";
        },
        createDealActGeneratorItem(overrides = {}) {
          const normalizedDescription = typeof overrides.description === "string"
            ? overrides.description
            : this.defaultDealActLineDescription();
          const normalizedQuantity = overrides.quantity !== undefined && overrides.quantity !== null
            ? String(overrides.quantity)
            : this.defaultDealActLineQuantity();
          const normalizedUnit = typeof overrides.unit === "string" && overrides.unit.trim()
            ? overrides.unit.trim()
            : "час";
          const normalizedPrice = overrides.price !== undefined && overrides.price !== null
            ? String(overrides.price)
            : this.defaultDealActLinePrice();
          return {
            description: normalizedDescription,
            quantity: normalizedQuantity,
            unit: normalizedUnit,
            price: normalizedPrice,
          };
        },
        async loadDealDocumentGeneratorContracts() {
          const companyId = this.dealDocumentGeneratorCompanyId();
          if (!companyId) {
            this.dealDocumentGeneratorContracts = [];
            return;
          }
          const payload = await this.apiRequest(`/api/v1/settlements/contracts/?client=${companyId}&page_size=100`);
          this.dealDocumentGeneratorContracts = this.normalizePaginatedResponse(payload).map((item) => this.normalizeSettlementContract(item));
        },
        applyDealDocumentGeneratorContractDefaults(options = {}) {
          const force = !!options.force;
          const hourlyRate = Number(this.selectedDealDocumentGeneratorHourlyRate || 0);
          const items = Array.isArray(this.dealActGeneratorForm.items) ? this.dealActGeneratorForm.items.slice() : [];
          if (!items.length) {
            this.dealActGeneratorForm.items = [this.createDealActGeneratorItem()];
            return;
          }
          const nextItems = items.map((item, index) => {
            const nextItem = { ...item };
            if (hourlyRate > 0 && (force || !String(nextItem.price || "").trim())) {
              nextItem.price = hourlyRate.toFixed(2);
            }
            if (index === 0 && (force || !String(nextItem.quantity || "").trim() || String(nextItem.quantity || "").trim() === "1")) {
              nextItem.quantity = this.defaultDealActLineQuantity(hourlyRate);
            }
            if (!String(nextItem.description || "").trim()) {
              nextItem.description = this.defaultDealActLineDescription();
            }
            if (!String(nextItem.unit || "").trim()) {
              nextItem.unit = "час";
            }
            return nextItem;
          });
          this.dealActGeneratorForm = {
            ...this.dealActGeneratorForm,
            items: nextItems,
          };
        },
        handleDealDocumentGeneratorContractChange() {
          this.applyDealDocumentGeneratorContractDefaults({ force: true });
        },
        resetDealDocumentGeneratorState() {
          this.showDealActGenerator = false;
          this.dealDocumentGeneratorType = "";
          this.dealDocumentGeneratorMode = "create";
          this.dealDocumentGeneratorTargetDocumentId = null;
          this.dealDocumentGeneratorTargetName = "";
          this.dealDocumentGeneratorContracts = [];
          this.dealActGeneratorForm = {
            executorCompanyId: null,
            contractId: null,
            items: [],
          };
        },
        resetDealActGeneratorForm() {
          this.dealActGeneratorForm = {
            executorCompanyId: this.preferredOwnCompanyId(),
            contractId: this.preferredDealDocumentGeneratorContractId(),
            items: [this.createDealActGeneratorItem()],
          };
          this.applyDealDocumentGeneratorContractDefaults({ force: true });
        },
        hydrateDealDocumentGeneratorForm(payload = {}) {
          const normalizedPayload = payload && typeof payload === "object" ? payload : {};
          const items = Array.isArray(normalizedPayload.items) && normalizedPayload.items.length
            ? normalizedPayload.items.map((item) => this.createDealActGeneratorItem(item))
            : [this.createDealActGeneratorItem({ description: "", quantity: "1", price: "" })];
          this.dealActGeneratorForm = {
            executorCompanyId: this.toIntOrNull(normalizedPayload.executor_company_id || normalizedPayload.executorCompanyId) || this.preferredOwnCompanyId(),
            contractId: this.toIntOrNull(normalizedPayload.contract_id || normalizedPayload.contractId) || this.preferredDealDocumentGeneratorContractId(),
            items,
          };
          this.applyDealDocumentGeneratorContractDefaults();
        },
        async ensureOwnCompaniesLoaded() {
          if (Array.isArray(this.ownCompanyOptions) && this.ownCompanyOptions.length) {
            return;
          }
          const payload = await this.apiRequest("/api/v1/clients/?company_type=own&page_size=200");
          const records = this.normalizePaginatedResponse(payload).map((item) => this.mapClient(item));
          this.datasets.companies = this.mergeSectionRecords(this.datasets.companies, records);
        },
        async openDealDocumentGenerator(type = "act") {
          if (!this.editingDealId || this.isDealDocumentUploading || this.isDealActGenerating || this.isDealActGeneratorPreparing) {
            return;
          }
          this.dealDocumentGeneratorType = String(type || "act").trim() === "invoice" ? "invoice" : "act";
          this.isDealActGeneratorPreparing = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.ensureOwnCompaniesLoaded();
            await this.loadDealDocumentGeneratorContracts();
            this.dealDocumentGeneratorMode = "create";
            this.dealDocumentGeneratorTargetDocumentId = null;
            this.dealDocumentGeneratorTargetName = "";
            this.resetDealActGeneratorForm();
            this.showDealActGenerator = true;
          } catch (error) {
            this.setUiError(`Ошибка подготовки ${this.dealDocumentGeneratorMeta.openErrorLabel}: ${error.message}`, { modal: true });
            this.resetDealDocumentGeneratorState();
          } finally {
            this.isDealActGeneratorPreparing = false;
          }
        },
        async openDealActGenerator() {
          await this.openDealDocumentGenerator("act");
        },
        async openDealInvoiceGenerator() {
          await this.openDealDocumentGenerator("invoice");
        },
        async openDealGeneratedDocumentEditor(documentItem) {
          if (!this.editingDealId || !documentItem?.editableGeneratedDocument || this.isDealDocumentUploading || this.isDealActGenerating || this.isDealActGeneratorPreparing) {
            return;
          }
          const documentType = String(documentItem.generatedDocumentType || "").trim();
          if (documentType !== "invoice" && documentType !== "realization") {
            return;
          }
          this.dealDocumentGeneratorType = documentType === "invoice" ? "invoice" : "act";
          this.dealDocumentGeneratorMode = "edit";
          this.dealDocumentGeneratorTargetDocumentId = this.toIntOrNull(documentItem.id);
          this.dealDocumentGeneratorTargetName = String(documentItem.originalName || "").trim();
          this.isDealActGeneratorPreparing = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            await this.ensureOwnCompaniesLoaded();
            await this.loadDealDocumentGeneratorContracts();
            this.hydrateDealDocumentGeneratorForm(documentItem.generatorPayload || {});
            this.showDealActGenerator = true;
          } catch (error) {
            this.setUiError(`Ошибка подготовки ${this.dealDocumentGeneratorMeta.openErrorLabel}: ${error.message}`, { modal: true });
            this.resetDealDocumentGeneratorState();
          } finally {
            this.isDealActGeneratorPreparing = false;
          }
        },
        closeDealActGenerator() {
          this.resetDealDocumentGeneratorState();
        },
        addDealActGeneratorItem() {
          const lastItem = Array.isArray(this.dealActGeneratorForm.items) && this.dealActGeneratorForm.items.length
            ? this.dealActGeneratorForm.items[this.dealActGeneratorForm.items.length - 1]
            : null;
          const hourlyRate = Number(this.selectedDealDocumentGeneratorHourlyRate || 0);
          this.dealActGeneratorForm.items = [
            ...(this.dealActGeneratorForm.items || []),
            this.createDealActGeneratorItem({
              description: "",
              quantity: "1",
              unit: lastItem?.unit || "час",
              price: hourlyRate > 0 ? hourlyRate.toFixed(2) : (lastItem?.price || ""),
            }),
          ];
        },
        removeDealActGeneratorItem(index) {
          const items = Array.isArray(this.dealActGeneratorForm.items) ? this.dealActGeneratorForm.items.slice() : [];
          if (items.length <= 1) {
            this.dealActGeneratorForm.items = [this.createDealActGeneratorItem({ description: "", quantity: this.defaultDealActLineQuantity(), price: this.defaultDealActLinePrice() })];
            return;
          }
          items.splice(index, 1);
          this.dealActGeneratorForm.items = items;
        },
        dealActGeneratorItemTotal(item) {
          return this.parseFlexibleNumber(item?.quantity) * this.parseFlexibleNumber(item?.price);
        },
        buildDealActGeneratorPayload() {
          const executorCompanyId = this.toIntOrNull(this.dealActGeneratorForm.executorCompanyId);
          if (!executorCompanyId) {
            throw new Error("Выберите собственную организацию.");
          }
          const normalizedItems = (this.dealActGeneratorForm.items || []).map((item, index) => {
            const description = String(item?.description || "").trim();
            const quantity = this.parseFlexibleNumber(item?.quantity);
            const price = this.parseFlexibleNumber(item?.price);
            const unit = String(item?.unit || "").trim() || "час";
            const rowNumber = index + 1;
            if (!description) {
              throw new Error(`Заполните наименование в строке ${rowNumber}.`);
            }
            if (quantity <= 0) {
              throw new Error(`Укажите количество больше нуля в строке ${rowNumber}.`);
            }
            if (price <= 0) {
              throw new Error(`Укажите стоимость больше нуля в строке ${rowNumber}.`);
            }
            return {
              description,
              quantity: quantity.toFixed(2),
              unit,
              price: price.toFixed(2),
            };
          });
          if (!normalizedItems.length) {
            throw new Error(this.dealDocumentGeneratorMeta.emptyItemsMessage);
          }
          return {
            deal: this.editingDealId,
            executor_company: executorCompanyId,
            contract: this.toIntOrNull(this.dealActGeneratorForm.contractId),
            items: normalizedItems,
          };
        },
        mapDealDocument(item) {
          return {
            id: item.id,
            scope: "deal",
            dealId: this.toIntOrNull(item.deal),
            originalName: item.original_name || item.originalName || "",
            fileUrl: item.download_url || item.downloadUrl || item.file_url || item.fileUrl || "",
            fileSize: Number.parseInt(item.file_size || item.fileSize || 0, 10) || 0,
            settlementDocumentId: this.toIntOrNull(item.settlement_document_id || item.settlementDocumentId),
            generatedDocumentType: String(item.generated_document_type || item.generatedDocumentType || "").trim(),
            editableGeneratedDocument: !!(item.editable_generated_document ?? item.editableGeneratedDocument),
            generatorPayload: (item.generator_payload && typeof item.generator_payload === "object")
              ? item.generator_payload
              : (item.generatorPayload && typeof item.generatorPayload === "object" ? item.generatorPayload : {}),
            uploadedByName: item.uploaded_by_name || item.uploadedByName || "",
            createdAt: item.created_at || item.createdAt || "",
          };
        },
        mapClientDocument(item) {
          return {
            id: item.id,
            scope: "company",
            clientId: this.toIntOrNull(item.client),
            originalName: item.original_name || item.originalName || "",
            fileUrl: item.download_url || item.downloadUrl || item.file_url || item.fileUrl || "",
            fileSize: Number.parseInt(item.file_size || item.fileSize || 0, 10) || 0,
            uploadedByName: item.uploaded_by_name || item.uploadedByName || "",
            createdAt: item.created_at || item.createdAt || "",
          };
        },
        async loadDealDocuments() {
          const dealId = this.toIntOrNull(this.editingDealId);
          if (!dealId) {
            this.dealDocumentsForActiveDeal = [];
            return;
          }
          this.isDealDocumentsLoading = true;
          try {
            const payload = await this.apiRequest(`/api/v1/deal-documents/?deal=${dealId}&page_size=100`);
            const records = Array.isArray(payload?.results) ? payload.results : (Array.isArray(payload) ? payload : []);
            this.dealDocumentsForActiveDeal = records.map((item) => this.mapDealDocument(item));
          } finally {
            this.isDealDocumentsLoading = false;
          }
        },
        async loadCompanyDocuments() {
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!companyId) {
            this.companyDocumentsForActiveCompany = [];
            this.companyDealDocumentGroups = [];
            this.companySettlementContracts = [];
            return;
          }
          this.isCompanyDocumentsLoading = true;
          try {
            const [companyPayload, contractsPayload] = await Promise.all([
              this.apiRequest(`/api/v1/client-documents/?client=${companyId}&page_size=100`),
              this.apiRequest(`/api/v1/settlements/contracts/?client=${companyId}&page_size=100`),
            ]);
            const companyRecords = Array.isArray(companyPayload?.results) ? companyPayload.results : (Array.isArray(companyPayload) ? companyPayload : []);
            this.companyDocumentsForActiveCompany = companyRecords.map((item) => this.mapClientDocument(item));
            this.companySettlementContracts = this.normalizePaginatedResponse(contractsPayload).map((item) => this.normalizeSettlementContract(item));

            const deals = (this.datasets.deals || [])
              .filter((deal) => String(deal.clientId || "") === String(companyId))
              .slice()
              .sort((left, right) => String(left.title || left.name || "").localeCompare(String(right.title || right.name || ""), "ru"));

            const groups = await Promise.all(deals.map(async (deal) => {
              const payload = await this.apiRequest(`/api/v1/deal-documents/?deal=${deal.id}&page_size=100`);
              const records = Array.isArray(payload?.results) ? payload.results : (Array.isArray(payload) ? payload : []);
              return {
                dealId: deal.id,
                dealTitle: deal.title || deal.name || `Сделка #${deal.id}`,
                documents: records.map((item) => this.mapDealDocument(item)),
              };
            }));
            this.companyDealDocumentGroups = groups;
          } finally {
            this.isCompanyDocumentsLoading = false;
          }
        },
        openCompanyDocumentPicker() {
          if (!this.editingCompanyId || this.isCompanyDocumentUploading) {
            return;
          }
          const input = this.$refs.companyDocumentInput;
          if (input) {
            input.click();
          }
        },
        async handleCompanyDocumentInput(event) {
          const input = event?.target;
          const file = input?.files && input.files[0] ? input.files[0] : null;
          const companyId = this.toIntOrNull(this.editingCompanyId);
          if (!file || !companyId) {
            if (input) input.value = "";
            return;
          }
          const formData = new FormData();
          formData.append("client", String(companyId));
          formData.append("file", file);
          formData.append("original_name", file.name || "");
          this.isCompanyDocumentUploading = true;
          try {
            const created = await this.apiRequest("/api/v1/client-documents/", {
              method: "POST",
              body: formData,
            });
            this.companyDocumentsForActiveCompany = [
              this.mapClientDocument(created),
              ...this.companyDocumentsForActiveCompany,
            ];
            this.showCompanyDocumentsPanel = true;
          } finally {
            this.isCompanyDocumentUploading = false;
            if (input) input.value = "";
          }
        },
        sanitizeTouchDocumentSelection() {
          const allowedDealIds = new Set(this.touchDealDocuments.map((item) => String(item.id)));
          const allowedClientIds = new Set(this.touchCompanyDocuments.map((item) => String(item.id)));
          this.forms.touches.dealDocumentIds = (this.forms.touches.dealDocumentIds || []).filter((id) => allowedDealIds.has(String(id)));
          this.forms.touches.clientDocumentIds = (this.forms.touches.clientDocumentIds || []).filter((id) => allowedClientIds.has(String(id)));
        },
        async loadTouchDocuments() {
          const companyId = this.toIntOrNull(this.forms.touches.companyId);
          const dealId = this.toIntOrNull(this.forms.touches.dealId);
          this.isTouchDocumentsLoading = true;
          try {
            const [companyPayload, dealPayload] = await Promise.all([
              companyId ? this.apiRequest(`/api/v1/client-documents/?client=${companyId}&page_size=100`) : Promise.resolve([]),
              dealId ? this.apiRequest(`/api/v1/deal-documents/?deal=${dealId}&page_size=100`) : Promise.resolve([]),
            ]);
            const companyRecords = Array.isArray(companyPayload?.results) ? companyPayload.results : (Array.isArray(companyPayload) ? companyPayload : []);
            const dealRecords = Array.isArray(dealPayload?.results) ? dealPayload.results : (Array.isArray(dealPayload) ? dealPayload : []);
            this.touchCompanyDocuments = companyRecords.map((item) => this.mapClientDocument(item));
            this.touchDealDocuments = dealRecords.map((item) => this.mapDealDocument(item));
            this.sanitizeTouchDocumentSelection();
            if (!this.forms.touches.documentUploadTarget) {
              this.forms.touches.documentUploadTarget = dealId ? "deal" : (companyId ? "company" : "");
            }
          } finally {
            this.isTouchDocumentsLoading = false;
          }
        },
        openTouchDocumentPicker() {
          if (this.isTouchDocumentUploading) {
            return;
          }
          const input = this.$refs.touchDocumentInput;
          if (input) {
            input.click();
          }
        },
        async handleTouchDocumentInput(event) {
          const input = event?.target;
          const file = input?.files && input.files[0] ? input.files[0] : null;
          const uploadTarget = String(this.forms.touches.documentUploadTarget || "");
          const dealId = this.toIntOrNull(this.forms.touches.dealId);
          const companyId = this.toIntOrNull(this.forms.touches.companyId);
          if (!file || (uploadTarget !== "deal" && uploadTarget !== "company")) {
            if (input) input.value = "";
            return;
          }
          if (uploadTarget === "deal" && !dealId) {
            this.setUiError("Для загрузки документа в сделку выберите сделку.", { modal: true });
            if (input) input.value = "";
            return;
          }
          if (uploadTarget === "company" && !companyId) {
            this.setUiError("Для загрузки документа в компанию выберите компанию.", { modal: true });
            if (input) input.value = "";
            return;
          }
          const formData = new FormData();
          formData.append(uploadTarget === "deal" ? "deal" : "client", String(uploadTarget === "deal" ? dealId : companyId));
          formData.append("file", file);
          formData.append("original_name", file.name || "");
          this.isTouchDocumentUploading = true;
          try {
            const created = await this.apiRequest(uploadTarget === "deal" ? "/api/v1/deal-documents/" : "/api/v1/client-documents/", {
              method: "POST",
              body: formData,
            });
            if (uploadTarget === "deal") {
              const mapped = this.mapDealDocument(created);
              this.touchDealDocuments = [mapped, ...this.touchDealDocuments];
              this.forms.touches.dealDocumentIds = [mapped.id, ...(this.forms.touches.dealDocumentIds || [])];
            } else {
              const mapped = this.mapClientDocument(created);
              this.touchCompanyDocuments = [mapped, ...this.touchCompanyDocuments];
              this.forms.touches.clientDocumentIds = [mapped.id, ...(this.forms.touches.clientDocumentIds || [])];
            }
          } finally {
            this.isTouchDocumentUploading = false;
            if (input) input.value = "";
          }
        },
        async toggleDealDocumentsPanel() {
          if (!this.editingDealId) {
            return;
          }
          this.showDealDocumentsPanel = !this.showDealDocumentsPanel;
          if (this.showDealDocumentsPanel) {
            this.showDealContactsPanel = false;
            this.showDealTaskForm = false;
            this.showDealCommunicationsPanel = false;
            this.showDealPhoneCallHistory = false;
            this.stopCommunicationsPollingIfIdle();
            await this.loadDealDocuments();
            this.scrollPanelIntoView("deal-documents-panel");
          }
        },
        async toggleDealPhoneCallHistoryPanel() {
          if (!this.editingDealId) {
            return;
          }
          this.showDealPhoneCallHistory = !this.showDealPhoneCallHistory;
          if (this.showDealPhoneCallHistory) {
            this.showDealContactsPanel = false;
            this.showDealTaskForm = false;
            this.showDealCommunicationsPanel = false;
            this.showDealDocumentsPanel = false;
            this.stopCommunicationsPollingIfIdle();
            await this.ensurePhoneCallHistoryLoaded("deal", this.editingDealId);
            this.scrollPanelIntoView("deal-phone-history-panel");
          }
        },
        openDealDocumentPicker() {
          if (!this.editingDealId || this.isDealDocumentUploading || this.isDealActGenerating) {
            return;
          }
          const input = this.$refs.dealDocumentInput;
          if (input) {
            input.click();
          }
        },
        async generateDealDocumentFromGenerator() {
          if (!this.editingDealId) {
            return;
          }
          this.isDealActGenerating = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            const payload = this.buildDealActGeneratorPayload();
            const created = await this.apiRequest(this.dealDocumentGeneratorMeta.endpoint, {
              method: "POST",
              body: payload,
            });
            const mappedDocument = this.mapDealDocument(created);
            if (this.dealDocumentGeneratorMode === "edit") {
              this.dealDocumentsForActiveDeal = (this.dealDocumentsForActiveDeal || []).map((item) => (
                String(item.id) === String(mappedDocument.id) ? mappedDocument : item
              ));
              if (this.dealDocumentSendTarget && String(this.dealDocumentSendTarget.id) === String(mappedDocument.id)) {
                this.dealDocumentSendTarget = mappedDocument;
              }
            } else {
              this.dealDocumentsForActiveDeal = [
                mappedDocument,
                ...this.dealDocumentsForActiveDeal,
              ];
            }
            const activeDeal = this.editingDealItem;
            const generatedDealClientId = this.toIntOrNull(activeDeal?.clientId);
            const openedCompanyId = this.toIntOrNull(this.editingCompanyId);
            if (generatedDealClientId && openedCompanyId && generatedDealClientId === openedCompanyId) {
              if (this.showCompanySettlementsPanel) {
                await this.loadCompanySettlements();
              }
              if (this.showCompanyDocumentsPanel) {
                await this.loadCompanyDocuments();
              }
            }
            this.showDealDocumentsPanel = true;
            this.resetDealDocumentGeneratorState();
          } catch (error) {
            const operationLabel = this.dealDocumentGeneratorMode === "edit"
              ? (this.dealDocumentGeneratorType === "invoice" ? "сохранения счета" : "сохранения акта")
              : this.dealDocumentGeneratorMeta.generateErrorLabel;
            this.setUiError(`Ошибка ${operationLabel}: ${error.message}`, { modal: true });
          } finally {
            this.isDealActGenerating = false;
          }
        },
        async handleDealDocumentInput(event) {
          const input = event?.target;
          const file = input?.files && input.files[0] ? input.files[0] : null;
          if (!file || !this.editingDealId) {
            if (input) input.value = "";
            return;
          }
          const formData = new FormData();
          formData.append("deal", String(this.editingDealId));
          formData.append("file", file);
          formData.append("original_name", file.name || "");
          this.isDealDocumentUploading = true;
          try {
            const created = await this.apiRequest("/api/v1/deal-documents/", {
              method: "POST",
              body: formData,
            });
            this.dealDocumentsForActiveDeal = [
              this.mapDealDocument(created),
              ...this.dealDocumentsForActiveDeal,
            ];
            this.showDealDocumentsPanel = true;
          } finally {
            this.isDealDocumentUploading = false;
            if (input) input.value = "";
          }
        },
        quickAddLeadTouch() {
          this.modalParentContext = this.captureModalParentContext();
          this.activeSection = "touches";
          this.editingTouchId = null;
          this.showAllTouchResults = false;
          this.forms.touches = {
            ...this.getDefaultForm("touches"),
            happenedAt: this.toDateTimeLocal(new Date().toISOString()),
            companyId: this.toIntOrNull(this.editingLeadItem?.clientId),
            leadId: this.toIntOrNull(this.editingLeadId),
            ownerId: this.resolveTouchOwnerIdFromContext({
              leadId: this.editingLeadId,
              companyId: this.editingLeadItem?.clientId,
            }),
            documentUploadTarget: this.toIntOrNull(this.editingLeadItem?.clientId) ? "company" : "",
          };
          this.loadTouchDocuments();
          this.showModal = true;
          this.$nextTick(() => this.applyTouchAutomationRule());
        },
        quickAddLeadTask() {
          this.activeSection = "tasks";
          this.editingTaskId = null;
          this.forms.tasks = {
            ...this.getDefaultForm("tasks"),
            companyId: this.toIntOrNull(this.editingLeadItem?.clientId),
            leadId: this.toIntOrNull(this.editingLeadId),
          };
          this.resetTaskFollowUpForm();
          this.showModal = true;
          this.loadTaskTouchOptions();
        },
        scrollToLeadTasksPanel() {
          this.$nextTick(() => {
            const panel = document.getElementById("lead-task-panel");
            if (panel && typeof panel.scrollIntoView === "function") {
              panel.scrollIntoView({ behavior: "smooth", block: "start" });
            }
          });
        },
        openTaskFromLead(task) {
          this.openTaskEditor(task, { parentContext: this.modalParentContext || this.captureModalParentContext() });
        },
        async toggleLeadDocumentsPanel() {
          this.showLeadDocumentsPanel = !this.showLeadDocumentsPanel;
          if (this.showLeadDocumentsPanel) {
            this.showLeadPhoneCallHistory = false;
            await this.loadLeadDocuments();
          }
        },
        async toggleLeadPhoneCallHistoryPanel() {
          if (!this.editingLeadId) {
            return;
          }
          this.showLeadPhoneCallHistory = !this.showLeadPhoneCallHistory;
          if (this.showLeadPhoneCallHistory) {
            this.showLeadDocumentsPanel = false;
            await this.ensurePhoneCallHistoryLoaded("lead", this.editingLeadId);
          }
        },
        openLeadDocumentPicker() {
          if (!this.editingLeadId || this.isLeadDocumentUploading) {
            return;
          }
          const input = this.$refs.leadDocumentInput;
          if (input) {
            input.click();
          }
        },
        mapLeadDocument(item) {
          return {
            id: item.id,
            scope: "lead",
            leadId: this.toIntOrNull(item.lead),
            originalName: item.original_name || item.originalName || "",
            fileUrl: item.download_url || item.downloadUrl || item.file_url || item.fileUrl || "",
            fileSize: Number.parseInt(item.file_size || item.fileSize || 0, 10) || 0,
            uploadedByName: item.uploaded_by_name || item.uploadedByName || "",
            createdAt: item.created_at || item.createdAt || "",
          };
        },
        async loadLeadDocuments() {
          const leadId = this.toIntOrNull(this.editingLeadId);
          if (!leadId) {
            this.leadDocumentsForActiveLead = [];
            return;
          }
          this.isLeadDocumentsLoading = true;
          try {
            const payload = await this.apiRequest(`/api/v1/lead-documents/?lead=${leadId}&page_size=100`);
            const records = Array.isArray(payload?.results) ? payload.results : (Array.isArray(payload) ? payload : []);
            this.leadDocumentsForActiveLead = records.map((item) => this.mapLeadDocument(item));
          } finally {
            this.isLeadDocumentsLoading = false;
          }
        },
        async handleLeadDocumentInput(event) {
          const input = event?.target;
          const file = input?.files && input.files[0] ? input.files[0] : null;
          const leadId = this.toIntOrNull(this.editingLeadId);
          if (!file || !leadId) {
            if (input) input.value = "";
            return;
          }
          const formData = new FormData();
          formData.append("lead", String(leadId));
          formData.append("file", file);
          formData.append("original_name", file.name || "");
          this.isLeadDocumentUploading = true;
          try {
            const created = await this.apiRequest("/api/v1/lead-documents/", {
              method: "POST",
              body: formData,
            });
            this.leadDocumentsForActiveLead = [
              this.mapLeadDocument(created),
              ...this.leadDocumentsForActiveLead,
            ];
            this.showLeadDocumentsPanel = true;
          } finally {
            this.isLeadDocumentUploading = false;
            if (input) input.value = "";
          }
        },
        resolveCompanyRegionLabel(address) {
          const chunks = String(address || "")
            .split(",")
            .map((chunk) => chunk.trim())
            .filter(Boolean);
          if (!chunks.length) {
            return "Не указан";
          }
          return chunks.slice(0, 2).join(", ");
        },
        isCompanySummaryEditing(fieldKey) {
          return String(this.companySummaryEditingField || "") === String(fieldKey || "");
        },
        startCompanySummaryEdit(fieldKey) {
          this.companySummaryEditingField = String(fieldKey || "");
        },
        stopCompanySummaryEdit(fieldKey = "") {
          if (!fieldKey || this.isCompanySummaryEditing(fieldKey)) {
            this.companySummaryEditingField = "";
          }
        },
        isLeadSummaryEditing(fieldKey) {
          return String(this.leadSummaryEditingField || "") === String(fieldKey || "");
        },
        startLeadSummaryEdit(fieldKey) {
          this.leadSummaryEditingField = String(fieldKey || "");
        },
        stopLeadSummaryEdit(fieldKey = "") {
          if (!fieldKey || this.isLeadSummaryEditing(fieldKey)) {
            this.leadSummaryEditingField = "";
          }
        },
        isTaskSummaryEditing(fieldKey) {
          return String(this.taskSummaryEditingField || "") === String(fieldKey || "");
        },
        startTaskSummaryEdit(fieldKey) {
          this.taskSummaryEditingField = String(fieldKey || "");
        },
        stopTaskSummaryEdit(fieldKey = "") {
          if (!fieldKey || this.isTaskSummaryEditing(fieldKey)) {
            this.taskSummaryEditingField = "";
          }
        },
        openLeadSummaryField(fieldKey) {
          if (fieldKey === "lastTouch") {
            if (this.leadSummaryLastTouch) {
              this.openTouchEditor(this.leadSummaryLastTouch, { parentContext: this.captureModalParentContext() });
            }
            return;
          }
          if (fieldKey === "nextAction") {
            const nextAction = this.leadSummaryNextAction;
            if (nextAction?.item) {
              if (nextAction.item.dueAtRaw || nextAction.item.taskStatus) {
                this.openTaskEditor(nextAction.item);
                return;
              }
              this.openTouchEditor(nextAction.item, { parentContext: this.captureModalParentContext() });
              return;
            }
          }
          this.startLeadSummaryEdit(fieldKey);
        },
        openTaskSummaryField(fieldKey) {
          if (fieldKey === "relatedTouchId") {
            const touchId = this.toIntOrNull(this.forms.tasks.relatedTouchId);
            if (touchId) {
              this.openTouchFromEvent(touchId);
              return;
            }
          }
          this.startTaskSummaryEdit(fieldKey);
        },
        companyWorkRuleDecisionMakerLabel() {
          const decisionMakerId = this.toIntOrNull(this.forms.companies.workRules.decisionMakerId);
          if (!decisionMakerId) return "Не выбран";
          const contact = (this.companyContactsForActiveCompany || []).find((item) => String(item.id) === String(decisionMakerId));
          return contact?.fullName || "Не выбран";
        },
        companyWorkRuleChannelsLabel() {
          const selectedIds = Array.isArray(this.forms.companies.workRules.communicationChannelIds)
            ? this.forms.companies.workRules.communicationChannelIds.map((value) => String(value))
            : [];
          const selected = (this.metaOptions.communicationChannels || []).filter((channel) => selectedIds.includes(String(channel.id)));
          return selected.length ? selected.map((channel) => channel.name).join(", ") : "Не выбраны";
        },
        openCompanySummaryField(fieldKey) {
          if (fieldKey === "activeDeal") {
            if (this.companySummaryCurrentDeal) {
              this.openDealEditor(this.companySummaryCurrentDeal);
            }
            return;
          }
          if (fieldKey === "lastTouch") {
            if (this.companySummaryLastTouch) {
              this.openTouchEditor(this.companySummaryLastTouch);
            }
            return;
          }
          if (fieldKey === "nextAction") {
            const action = this.companySummaryNextAction;
            if (action?.type === "task" && action.item) {
              this.openTaskEditor(action.item);
              return;
            }
            if (action?.type === "touch" && action.item) {
              this.openTouchEditor(action.item);
              return;
            }
            this.activeSection = "touches";
            this.editingTouchId = null;
            this.forms.touches = {
              ...this.getDefaultForm("touches"),
              happenedAt: this.toDateTimeLocal(new Date().toISOString()),
              companyId: this.toIntOrNull(this.editingCompanyId),
              ownerId: this.resolveTouchOwnerIdFromContext({
                companyId: this.editingCompanyId,
              }),
            };
            this.showModal = true;
            return;
          }
          this.startCompanySummaryEdit(fieldKey);
        },
        dealTouchesByDealId(dealId) {
          const normalizedDealId = this.toIntOrNull(dealId);
          if (!normalizedDealId) return [];
          return (this.datasets.touches || []).filter((touch) => String(touch.dealId || "") === String(normalizedDealId));
        },
        dealUpcomingTasksByDealId(dealId) {
          const normalizedDealId = this.toIntOrNull(dealId);
          if (!normalizedDealId) return [];
          return (this.datasets.tasks || [])
            .filter((task) => (
              String(task.dealId || "") === String(normalizedDealId)
              && this.isTaskActiveStatus(task.taskStatus || task.status)
              && task.dueAtRaw
            ))
            .slice()
            .sort((left, right) => (
              (this.taskItemSatisfiesDealNextStepRequirement(left) ? 0 : 1) - (this.taskItemSatisfiesDealNextStepRequirement(right) ? 0 : 1)
              || (this.parseTaskDueTimestamp(left.dueAtRaw) || 0) - (this.parseTaskDueTimestamp(right.dueAtRaw) || 0)
            ));
        },
        dealLastTouchByDealId(dealId) {
          const touches = this.dealTouchesByDealId(dealId).slice();
          touches.sort((left, right) => (this.parseTaskDueTimestamp(right.happenedAtRaw) || 0) - (this.parseTaskDueTimestamp(left.happenedAtRaw) || 0));
          return touches[0] || null;
        },
        dealNextTouchByDealId(dealId) {
          const touches = this.dealTouchesByDealId(dealId)
            .filter((touch) => touch.nextStepAtRaw)
            .slice();
          touches.sort((left, right) => (this.parseTaskDueTimestamp(left.nextStepAtRaw) || 0) - (this.parseTaskDueTimestamp(right.nextStepAtRaw) || 0));
          return touches[0] || null;
        },
        dealNextActionSummaryByDealId(dealId) {
          const nextTask = this.dealUpcomingTasksByDealId(dealId)[0] || null;
          const nextTouch = this.dealNextTouchByDealId(dealId);
          if (nextTask) {
            return {
              title: nextTask.subject || nextTask.name || "Не указан",
              at: nextTask.dueAtRaw || null,
            };
          }
          if (nextTouch) {
            return {
              title: nextTouch.nextStep || nextTouch.summary || nextTouch.resultOptionName || "Не указан",
              at: nextTouch.nextStepAtRaw || null,
            };
          }
          return {
            title: "Не указан",
            at: null,
          };
        },
        dealLastTouchSummaryByDealId(dealId) {
          const lastTouch = this.dealLastTouchByDealId(dealId);
          if (!lastTouch) {
            return "Не указано";
          }
          return lastTouch.summary || lastTouch.resultOptionName || "Не указано";
        },
        dealOverdueRiskLabel(deal) {
          const normalizedDealId = this.toIntOrNull(deal?.id);
          if (!normalizedDealId) return "Не определён";
          const hasOverdueTask = (this.datasets.tasks || []).some((task) => (
            String(task.dealId || "") === String(normalizedDealId)
            && this.isTaskOverdue(task.dueAtRaw, task.taskStatus || task.status)
          ));
          if (hasOverdueTask || this.isDealOverdue(deal?.closeDate)) {
            return "Просрочено";
          }
          const nextAction = this.dealNextActionSummaryByDealId(normalizedDealId);
          const nextAt = this.parseTaskDueTimestamp(nextAction.at);
          if (nextAt !== null) {
            const diffDays = Math.ceil((nextAt - Date.now()) / 86400000);
            if (diffDays <= 1) return "Высокий";
            if (diffDays <= 3) return "Средний";
            return "Низкий";
          }
          return "Нет следующего шага";
        },
        companyFailedDealCompetitor(deal) {
          const metadata = deal?.metadata || {};
          return String(
            metadata.failed_competitor
            || metadata.competitor
            || metadata.lost_to_competitor
            || ""
          ).trim() || "—";
        },
        companyFailedDealCanReviveLabel(deal) {
          const metadata = deal?.metadata || {};
          const value = metadata.can_revive ?? metadata.can_reanimate ?? metadata.revive_possible;
          if (value === true) return "Да";
          if (value === false) return "Нет";
          if (value !== undefined && value !== null && String(value).trim()) return String(value).trim();
          return "—";
        },
        leadTouchesByLeadId(leadId) {
          const normalizedLeadId = this.toIntOrNull(leadId);
          if (!normalizedLeadId) return [];
          return (this.datasets.touches || []).filter((touch) => String(touch.leadId || "") === String(normalizedLeadId));
        },
        leadTasksByLeadId(leadId) {
          const normalizedLeadId = this.toIntOrNull(leadId);
          if (!normalizedLeadId) return [];
          return (this.datasets.tasks || []).filter((task) => String(task.leadId || "") === String(normalizedLeadId));
        },
        leadLastTouchByLeadId(leadId) {
          const touches = this.leadTouchesByLeadId(leadId).slice();
          touches.sort((left, right) => (this.parseTaskDueTimestamp(right.happenedAtRaw) || 0) - (this.parseTaskDueTimestamp(left.happenedAtRaw) || 0));
          return touches[0] || null;
        },
        leadUpcomingTasksByLeadId(leadId) {
          const now = Date.now();
          return this.leadTasksByLeadId(leadId)
            .filter((task) => this.isTaskActiveStatus(task.taskStatus || task.status))
            .filter((task) => {
              const ts = this.parseTaskDueTimestamp(task.dueAtRaw);
              return ts !== null && ts >= now;
            })
            .slice()
            .sort((left, right) => (
              (this.taskItemUsesCommunicationChannel(left) ? 0 : 1) - (this.taskItemUsesCommunicationChannel(right) ? 0 : 1)
              || (this.parseTaskDueTimestamp(left.dueAtRaw) || 0) - (this.parseTaskDueTimestamp(right.dueAtRaw) || 0)
            ));
        },
        leadNextTouchByLeadId(leadId) {
          const now = Date.now();
          const touches = this.leadTouchesByLeadId(leadId)
            .filter((touch) => {
              const ts = this.parseTaskDueTimestamp(touch.nextStepAtRaw);
              return ts !== null && ts >= now;
            })
            .slice();
          touches.sort((left, right) => (this.parseTaskDueTimestamp(left.nextStepAtRaw) || 0) - (this.parseTaskDueTimestamp(right.nextStepAtRaw) || 0));
          return touches[0] || null;
        },
        leadNextActionSummaryByLeadId(leadId) {
          const nextTask = this.leadUpcomingTasksByLeadId(leadId)[0] || null;
          const nextTouch = this.leadNextTouchByLeadId(leadId);
          const nextTaskTs = this.parseTaskDueTimestamp(nextTask?.dueAtRaw);
          const nextTouchTs = this.parseTaskDueTimestamp(nextTouch?.nextStepAtRaw);
          if (nextTaskTs !== null && (nextTouchTs === null || nextTaskTs <= nextTouchTs)) {
            return {
              type: "task",
              item: nextTask,
              title: nextTask.subject || nextTask.name || "—",
              at: nextTask.dueAtRaw || null,
            };
          }
          if (nextTouchTs !== null) {
            return {
              type: "touch",
              item: nextTouch,
              title: nextTouch.nextStep || nextTouch.summary || nextTouch.resultOptionName || "—",
              at: nextTouch.nextStepAtRaw || null,
            };
          }
          return { type: "", item: null, title: "—", at: null };
        },
        leadTouchCountByLeadId(leadId) {
          return this.leadTouchesByLeadId(leadId).length;
        },
        leadConvertedDealByLeadId(leadId) {
          const normalizedLeadId = this.toIntOrNull(leadId);
          if (!normalizedLeadId) return null;
          const deals = (this.datasets.deals || [])
            .filter((deal) => String(deal.leadId || "") === String(normalizedLeadId))
            .slice()
            .sort((left, right) => {
              const leftTs = this.parseTaskDueTimestamp(left.createdAt || left.closedAt || left.closeDate) || 0;
              const rightTs = this.parseTaskDueTimestamp(right.createdAt || right.closedAt || right.closeDate) || 0;
              return rightTs - leftTs || Number(right.id || 0) - Number(left.id || 0);
            });
          return deals[0] || null;
        },
        leadResultLabel(lead) {
          if (!lead) return "—";
          const convertedDeal = this.leadConvertedDealByLeadId(lead.id);
          if (convertedDeal) {
            return `Создана сделка: ${convertedDeal.title || convertedDeal.name || `#${convertedDeal.id}`}`;
          }
          const description = String(lead.description || "").trim();
          if (description) {
            return description;
          }
          return lead.statusLabel || "—";
        },
        leadLossReasonLabel(lead) {
          if (!lead) return "—";
          const statusCode = String(lead.statusCode || lead.status || "").trim();
          if (!["lost", "unqualified", "spam", "archived"].includes(statusCode)) {
            return "—";
          }
          const description = String(lead.description || "").trim();
          return description || lead.statusLabel || "—";
        },
        leadWorkingDaysLabel(lead) {
          const startTs = this.parseTaskDueTimestamp(lead?.createdAt);
          if (startTs === null) return "—";
          const convertedDeal = this.leadConvertedDealByLeadId(lead?.id);
          const finishTs = this.parseTaskDueTimestamp(convertedDeal?.createdAt || lead?.convertedAt);
          const endTs = finishTs !== null ? finishTs : Date.now();
          const diffDays = Math.max(0, Math.floor((endTs - startTs) / 86400000));
          return `${diffDays} дн`;
        },
        openLeadFromCompanyPanel(lead) {
          this.activeSection = "leads";
          this.showStatusFilter = false;
          this.showDealCompanyFilter = false;
          this.showTaskCompanyFilter = false;
          this.showTaskCategoryFilter = false;
          this.showTaskDealFilter = false;
          this.showTouchCompanyFilter = false;
          this.showTouchDealFilter = false;
          this.openLeadEditor(lead);
        },
        openDealFromCompanyPanel(deal) {
          this.activeSection = "deals";
          this.showStatusFilter = false;
          this.showDealCompanyFilter = false;
          this.showTaskCompanyFilter = false;
          this.showTaskCategoryFilter = false;
          this.showTouchCompanyFilter = false;
          this.showTouchDealFilter = false;
          this.openDealEditor(deal);
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
            if (profile.ogrn) {
              this.forms.companies.ogrn = profile.ogrn;
            }
            if (profile.kpp) {
              this.forms.companies.kpp = profile.kpp;
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
            this.dealTasksForActiveDeal = this.sortTasksByListRules(tasks.map((item) => {
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
            }));
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
          const leadId = this.toIntOrNull(this.forms.tasks.leadId);
          if (!dealId && !clientId && !leadId) {
            this.taskTouchOptions = [];
            return;
          }

          const params = new URLSearchParams({ page_size: "100", exclude_type: "task" });
          if (dealId) params.set("deal", String(dealId));
          if (clientId) params.set("client", String(clientId));
          if (leadId) params.set("lead", String(leadId));

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
        async loadTouchContactsForSelectedCompany() {
          const companyId = this.toIntOrNull(this.forms.touches.companyId);
          if (!companyId) {
            return;
          }
          try {
            const payload = await this.apiRequest(`/api/v1/contacts/?client=${companyId}&page_size=100`);
            const contacts = this.normalizePaginatedResponse(payload).map((item) => this.mapContact(item));
            this.datasets.contacts = this.mergeSectionRecords(this.datasets.contacts, contacts);
          } catch (error) {
            this.setUiError(`Ошибка загрузки контактов для касания: ${error.message}`, { modal: true });
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
              telegram: item.telegram || "",
              whatsapp: item.whatsapp || "",
              maxContact: item.max_contact || "",
              roleId: item.role || null,
              role: item.role_name || "",
              personNote: item.person_note || "",
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
          this.activeSection = "contacts";
          this.openContactEditor({
            id: contact.id,
            fullName: contact.fullName || "",
            clientId: contact.clientId || this.toIntOrNull(this.forms.deals.companyId),
            position: contact.position || "",
            phone: contact.phone || "",
            email: contact.email || "",
            telegram: contact.telegram || "",
            whatsapp: contact.whatsapp || "",
            maxContact: contact.maxContact || "",
            roleId: this.toIntOrNull(contact.roleId),
            role: contact.role || "",
            personNote: contact.personNote || "",
            isPrimary: !!contact.isPrimary
          });
        },
        toggleCompanyContactsPanel() {
          this.toggleExclusiveCompanyPanel("contacts");
          if (this.showCompanyContactsPanel) {
            this.scrollPanelIntoView("company-contacts-panel");
          }
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
            telegram: "",
            whatsapp: "",
            maxContact: "",
            roleId: null,
            role: "",
            personNote: "",
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
              telegram: item.telegram || "",
              whatsapp: item.whatsapp || "",
              maxContact: item.max_contact || "",
              roleId: item.role || null,
              role: item.role_name || "",
              personNote: item.person_note || "",
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
          this.showTaskCompanyFilter = false;
          this.showTaskCategoryFilter = false;
          this.showTouchCompanyFilter = false;
          this.showTouchDealFilter = false;
          this.selectedStatusFilters = [];
          this.selectedTaskCompanyFilters = [];
          this.selectedTaskCategoryFilters = [];
          this.selectedTouchCompanyFilters = [];
          this.clearTouchDealFilter();
          this.openContactEditor({
            id: contact.id,
            fullName: contact.fullName || "",
            clientId: contact.clientId || this.editingCompanyId,
            position: contact.position || "",
            phone: contact.phone || "",
            email: contact.email || "",
            telegram: contact.telegram || "",
            whatsapp: contact.whatsapp || "",
            maxContact: contact.maxContact || "",
            roleId: this.toIntOrNull(contact.roleId),
            role: contact.role || "",
            personNote: contact.personNote || "",
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
            convertedAt: item.converted_at || null,
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
            websiteSessionId: item.website_session_id || "",
            events: item.events || "",
            clientId: item.client || null,
            createdAt: item.created_at || null
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
            leadId: item.lead || null,
            leadTitle: item.lead_title || "",
            ownerId: item.owner || null,
            ownerName: item.owner_name || "",
            stageId: item.stage || "",
            stageCode,
            stageName: item.stage_name || "",
            amount: item.amount ?? 0,
            currency: item.currency || "RUB",
            closeDate: item.close_date || "",
            failureReason: item.failure_reason || "",
            metadata: item.metadata || {},
            events: item.events || "",
            isWon: !!item.is_won,
            createdAt: item.created_at || null
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
            telegram: item.telegram || "",
            whatsapp: item.whatsapp || "",
            maxContact: item.max_contact || "",
            roleId: item.role || null,
            role: item.role_name || "",
            personNote: item.person_note || "",
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
            companyType: item.company_type || "client",
            address: item.address || "",
            actualAddress: item.actual_address || "",
            ogrn: item.ogrn || "",
            kpp: item.kpp || "",
            bankDetails: item.bank_details || "",
            settlementAccount: item.settlement_account || "",
            correspondentAccount: item.correspondent_account || "",
            iban: item.iban || "",
            bik: item.bik || "",
            bankName: item.bank_name || "",
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
            ownerId: item.owner || this.toIntOrNull(item.created_by) || null,
            ownerName: item.owner_name || "",
            description: item.description || "",
            checklist: this.normalizeTaskChecklist(item.checklist),
            result: item.result || "",
            saveCompanyNote: !!item.save_company_note,
            companyNote: item.company_note || "",
            taskTypeCategoryId: item.task_type_category || null,
            taskTypeCategoryName: item.task_type_category_name || "",
            taskTypeId: item.task_type || null,
            taskTypeName: item.task_type_name || "",
            communicationChannelId: item.communication_channel || null,
            communicationChannelName: item.communication_channel_name || "",
            priority: item.priority || "medium",
            reminderOffsetMinutes: Number(item.deadline_reminder_offset_minutes || 30),
            company: item.client_name || "",
            clientId: item.client || null,
            leadId: item.lead || null,
            leadTitle: item.lead_title || "",
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
            name: item.summary || item.result_option_name || `Касание #${item.id}`,
            summary: item.summary || "",
            resultOptionId: item.result_option || null,
            resultOptionName: item.result_option_name || "",
            resultOptionCode: item.result_option_code || "",
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
            deal: item.deal_title || "",
            dealTitle: item.deal_title || "",
            dealDocuments: Array.isArray(item.deal_documents) ? item.deal_documents.map((document) => this.mapDealDocument(document)) : [],
            clientDocuments: Array.isArray(item.client_documents) ? item.client_documents.map((document) => this.mapClientDocument(document)) : [],
          };
        },
        mapAutomationDraft(item) {
          return {
            id: item.id,
            draftKind: item.draft_kind || "",
            status: item.status || "",
            title: item.title || "",
            summary: item.summary || "",
            sourceEventType: item.source_event_type || "",
            automationRuleId: item.automation_rule || null,
            automationRuleEventType: item.automation_rule_event_type || "",
            automationRuleUiMode: item.automation_rule_ui_mode || "",
            automationRuleUiPriority: item.automation_rule_ui_priority || "medium",
            sourceTouchId: item.source_touch || null,
            sourceTouchSummary: item.source_touch_summary || "",
            sourceTouchHappenedAt: item.source_touch_happened_at || null,
            outcomeId: item.outcome || null,
            outcomeName: item.outcome_name || "",
            touchResultId: item.touch_result || null,
            touchResultName: item.touch_result_name || "",
            nextStepTemplateId: item.next_step_template || null,
            nextStepTemplateName: item.next_step_template_name || "",
            proposedChannelId: item.proposed_channel || null,
            proposedChannelName: item.proposed_channel_name || "",
            proposedDirection: item.proposed_direction || "",
            proposedNextStep: item.proposed_next_step || "",
            proposedNextStepAt: item.proposed_next_step_at || null,
            ownerId: item.owner || null,
            ownerName: item.owner_name || "",
            leadId: item.lead || null,
            leadTitle: item.lead_title || "",
            dealId: item.deal || null,
            dealTitle: item.deal_title || "",
            clientId: item.client || null,
            clientName: item.client_name || "",
            contactId: item.contact || null,
            contactName: item.contact_name || "",
            taskId: item.task || null,
            taskSubject: item.task_subject || "",
            actedById: item.acted_by || null,
            actedByName: item.acted_by_name || "",
            actedAt: item.acted_at || null,
            createdAt: item.created_at || null,
            updatedAt: item.updated_at || null,
            isPrimaryMessage: !!item.is_primary_message,
          };
        },
        mapAutomationQueueItem(item) {
          return {
            id: item.id,
            itemKind: item.item_kind || "",
            status: item.status || "",
            title: item.title || "",
            summary: item.summary || "",
            recommendedAction: item.recommended_action || "",
            sourceEventType: item.source_event_type || "",
            automationRuleId: item.automation_rule || null,
            automationRuleEventType: item.automation_rule_event_type || "",
            automationRuleUiMode: item.automation_rule_ui_mode || "",
            automationRuleUiPriority: item.automation_rule_ui_priority || "medium",
            sourceTouchId: item.source_touch || null,
            sourceTouchSummary: item.source_touch_summary || "",
            sourceTouchHappenedAt: item.source_touch_happened_at || null,
            outcomeId: item.outcome || null,
            outcomeName: item.outcome_name || "",
            touchResultId: item.touch_result || null,
            touchResultName: item.touch_result_name || "",
            nextStepTemplateId: item.next_step_template || null,
            nextStepTemplateName: item.next_step_template_name || "",
            proposedChannelId: item.proposed_channel || null,
            proposedChannelName: item.proposed_channel_name || "",
            proposedDirection: item.proposed_direction || "",
            proposedNextStep: item.proposed_next_step || "",
            proposedNextStepAt: item.proposed_next_step_at || null,
            ownerId: item.owner || null,
            ownerName: item.owner_name || "",
            leadId: item.lead || null,
            leadTitle: item.lead_title || "",
            dealId: item.deal || null,
            dealTitle: item.deal_title || "",
            clientId: item.client || null,
            clientName: item.client_name || "",
            contactId: item.contact || null,
            contactName: item.contact_name || "",
            taskId: item.task || null,
            taskSubject: item.task_subject || "",
            createdTaskId: item.created_task || null,
            createdTaskSubject: item.created_task_subject || "",
            conversationId: item.conversation_id || null,
            availableActions: Array.isArray(item.available_actions) ? item.available_actions : [],
            actedById: item.acted_by || null,
            actedByName: item.acted_by_name || "",
            actedAt: item.acted_at || null,
            createdAt: item.created_at || null,
            updatedAt: item.updated_at || null,
          };
        },
        mapAutomationMessageDraft(item) {
          return {
            id: item.id,
            status: item.status || "",
            title: item.title || "",
            messageSubject: item.message_subject || "",
            messageText: item.message_text || "",
            sourceEventType: item.source_event_type || "",
            automationRuleId: item.automation_rule || null,
            automationRuleEventType: item.automation_rule_event_type || "",
            automationRuleUiPriority: item.automation_rule_ui_priority || "medium",
            sourceTouchId: item.source_touch || null,
            sourceTouchSummary: item.source_touch_summary || "",
            sourceTouchHappenedAt: item.source_touch_happened_at || null,
            conversationId: this.toIntOrNull(item.conversation_id),
            proposedChannelId: item.proposed_channel || null,
            proposedChannelName: item.proposed_channel_name || "",
            ownerId: item.owner || null,
            ownerName: item.owner_name || "",
            leadId: item.lead || null,
            leadTitle: item.lead_title || "",
            dealId: item.deal || null,
            dealTitle: item.deal_title || "",
            clientId: item.client || null,
            clientName: item.client_name || "",
            contactId: item.contact || null,
            contactName: item.contact_name || "",
            actedById: item.acted_by || null,
            actedByName: item.acted_by_name || "",
            actedAt: item.acted_at || null,
            lastOutboundStatus: item.last_outbound_status || "",
            lastOutboundChannel: item.last_outbound_channel || "",
            lastOutboundRecipient: item.last_outbound_recipient || "",
            lastOutboundError: item.last_outbound_error || "",
            lastOutboundSentAt: item.last_outbound_sent_at || null,
            createdAt: item.created_at || null,
            updatedAt: item.updated_at || null,
          };
        },
        mapSectionRecords(section, records) {
          if (section === "leads") return records.map(this.mapLead);
          if (section === "deals") return records.map(this.mapDeal);
          if (section === "contacts") return records.map(this.mapContact);
          if (section === "companies") return records.map(this.mapClient);
          if (section === "tasks") return records.map(this.mapTask);
          if (section === "touches") return records.map(this.mapTouch);
          return [];
        },
        mergeSectionRecords(existingRecords, nextRecords) {
          const merged = [];
          const seenIds = new Set();
          [...(Array.isArray(existingRecords) ? existingRecords : []), ...(Array.isArray(nextRecords) ? nextRecords : [])]
            .forEach((item) => {
              const key = String(item?.id || "");
              if (!key || seenIds.has(key)) {
                return;
              }
              seenIds.add(key);
              merged.push(item);
            });
          return merged;
        },
        async loadSection(section, options = {}) {
          const endpoint = SECTION_ENDPOINTS[section];
          if (!endpoint) return;
          const { append = false, url = "", force = false } = options;
          const requestUrl = String(url || endpoint).trim();
          if (!requestUrl) return;
          const currentState = this.sectionCollectionState?.[section] || { loaded: false, next: "", isLoadingMore: false };
          if (append && (!currentState.next || currentState.isLoadingMore)) {
            return;
          }

          this.sectionCollectionState = {
            ...this.sectionCollectionState,
            [section]: {
              ...currentState,
              isLoadingMore: append,
            },
          };

          try {
            const payload = await this.apiRequest(requestUrl);
            const records = this.mapSectionRecords(section, this.normalizePaginatedResponse(payload));
            const nextUrl = String(payload?.next || "").trim();
            this.datasets[section] = append
              ? this.mergeSectionRecords(this.datasets[section], records)
              : records;
            this.sectionCollectionState = {
              ...this.sectionCollectionState,
              [section]: {
                loaded: true,
                next: nextUrl,
                isLoadingMore: false,
              },
            };
          } catch (error) {
            this.sectionCollectionState = {
              ...this.sectionCollectionState,
              [section]: {
                ...currentState,
                isLoadingMore: false,
              },
            };
            throw error;
          }
        },
        async loadAutomationDrafts() {
          const payload = await this.apiRequest("/api/v1/automation-drafts/?status=pending&page_size=200");
          const records = this.normalizePaginatedResponse(payload);
          this.datasets.automationDrafts = records.map((item) => this.mapAutomationDraft(item));
        },
        async loadAutomationQueue() {
          const payload = await this.apiRequest("/api/v1/automation-queue/?status=pending&page_size=200");
          const records = this.normalizePaginatedResponse(payload);
          this.datasets.automationQueue = records.map((item) => this.mapAutomationQueueItem(item));
        },
        async loadAutomationMessageDrafts() {
          const payload = await this.apiRequest("/api/v1/automation-message-drafts/?status=pending&page_size=200");
          const records = this.normalizePaginatedResponse(payload);
          this.datasets.automationMessageDrafts = records.map((item) => this.mapAutomationMessageDraft(item));
        },
        async loadAllSections() {
          this.isLoading = true;
          this.errorMessage = "";
          try {
            if (this.isCommunicationsSection) {
              await this.loadCommunicationsCompanies();
              await this.ensureCommunicationsCompanySelection();
            } else if (!this.isTelephonySection) {
              await this.loadSection(this.activeSection, { force: true });
            }
            if (this.sectionUsesAutomationData(this.activeSection)) {
              await this.ensureAutomationDataLoaded();
              this.ensureAutomationNotificationsPolling();
            }
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
            if (this.isTelephonySection) {
              await this.loadTelephonySettings(true);
            } else if (this.isCommunicationsSection) {
              await this.loadCommunicationsCompanies(true);
              await this.ensureCommunicationsCompanySelection({ preserveSelection: true });
            } else {
              await this.loadSection(this.activeSection, { force: true });
            }
            if (this.sectionUsesAutomationData(this.activeSection)) {
              await this.ensureAutomationDataLoaded(true);
              this.ensureAutomationNotificationsPolling();
            }
          } catch (error) {
            this.errorMessage = `Ошибка обновления: ${error.message}`;
          } finally {
            this.isLoading = false;
          }
        },
        async loadNextPageForActiveSection() {
          if (this.isTelephonySection || this.isCommunicationsSection) {
            return;
          }
          const section = String(this.activeSection || "").trim();
          const state = this.sectionCollectionState?.[section];
          if (!state?.next || state?.isLoadingMore) {
            return;
          }
          try {
            await this.loadSection(section, { append: true, url: state.next });
          } catch (error) {
            this.errorMessage = `Ошибка догрузки списка: ${error.message}`;
          }
        },
        handleListScroll(event) {
          const container = event?.target;
          if (!container || this.isLoading || this.activeSectionCollectionState?.isLoadingMore) {
            return;
          }
          const remaining = Number(container.scrollHeight || 0) - Number(container.scrollTop || 0) - Number(container.clientHeight || 0);
          if (remaining <= 180) {
            this.loadNextPageForActiveSection();
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
          this.clearTelephonyNotice();
          this.leadSummaryEditingField = "";
          this.taskSummaryEditingField = "";
          this.companySummaryEditingField = "";
          this.search = "";
          this.showStatusFilter = false;
          this.showDealCompanyFilter = false;
          this.showTaskCompanyFilter = false;
          this.showTaskCategoryFilter = false;
          this.showTaskDealFilter = false;
          this.showTouchCompanyFilter = false;
          this.showTouchDealFilter = false;
          this.showManagerNotifications = false;
          this.showManagerNotificationSidebar = false;
          this.closeDealDocumentSendSidebar();
          this.managerNotificationDraftPreviewId = "";
          this.activeManagerNotificationId = "";
          this.managerNotificationSidebarMode = "overview";
          this.managerNotificationReplyDraftId = "";
          this.managerNotificationReplyComposer = {
            subject: "",
            bodyText: "",
            recipient: "",
          };
          this.resetUnboundCommunicationsState();
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.resetExpandedOptionalFields();
          this.showDealTaskForm = false;
          this.resetDealTaskForm();
          this.resetTouchFollowUpForm();
          this.resetTaskFollowUpForm();
          this.taskTouchOptions = [];
          this.cancelSourceCreate();
          this.showDealCompanyForm = false;
          this.showDealContactsPanel = false;
          this.showDealDocumentsPanel = false;
          this.resetDealDocumentGeneratorState();
          this.showDealPhoneCallHistory = false;
          this.showLeadDocumentsPanel = false;
          this.showLeadPhoneCallHistory = false;
          this.resetDealCommunicationsState();
          this.showDealContactForm = false;
          this.resetDealCompanyForm();
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          this.dealDocumentsForActiveDeal = [];
          this.leadDocumentsForActiveLead = [];
          this.touchDealDocuments = [];
          this.touchCompanyDocuments = [];
          this.showCompanyContactForm = false;
          this.showCompanyContactsPanel = false;
          this.showCompanyDocumentsPanel = false;
          this.showCompanySettlementsPanel = false;
          this.showCompanyPhoneCallHistory = false;
          this.resetCompanyCommunicationsState();
          this.showCompanyRequisites = false;
          this.showCompanySettlementsPanel = false;
          this.showCompanyWorkRules = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyOkvedDetails = false;
          this.resetCompanyContactForm();
          this.companyContactsForActiveCompany = [];
          this.companyDocumentsForActiveCompany = [];
          this.companyDealDocumentGroups = [];
          this.resetCompanySettlementState();
          if (section !== "communications") {
            this.resetCommunicationsSectionState();
          }
          if (section === "telephony") {
            if (!this.telephonySettingsLoaded) {
              this.reloadActiveSection();
            } else {
              this.loadTelephonyHealth().catch(() => {});
            }
            return;
          }
          if (section === "communications" && this.isSectionLazyLoadingReady) {
            this.loadCommunicationsCompanies()
              .then(() => this.ensureCommunicationsCompanySelection())
              .catch((error) => {
                this.errorMessage = `Ошибка загрузки коммуникаций: ${error.message}`;
              });
            return;
          }
        },
        resetSearch() {
          this.search = "";
        },
        closeModal() {
          if ((this.activeSection === "touches" || this.activeSection === "tasks") && this.modalParentContext) {
            this.restoreModalParentContext();
            return;
          }
          this.showModal = false;
          this.modalParentContext = null;
          this.showAllTouchResults = false;
          this.leadSummaryEditingField = "";
          this.taskSummaryEditingField = "";
          this.companySummaryEditingField = "";
          this.cancelSourceCreate();
          this.clearUiErrors({ globalOnly: true });
          this.showDealCompanyFilter = false;
          this.showTouchCompanyFilter = false;
          this.showTouchDealFilter = false;
          this.showManagerNotifications = false;
          this.showManagerNotificationSidebar = false;
          this.closeDealDocumentSendSidebar();
          this.managerNotificationDraftPreviewId = "";
          this.activeManagerNotificationId = "";
          this.managerNotificationSidebarMode = "overview";
          this.managerNotificationReplyDraftId = "";
          this.managerNotificationReplyComposer = {
            subject: "",
            bodyText: "",
            recipient: "",
          };
          this.resetUnboundCommunicationsState();
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.resetExpandedOptionalFields();
          this.showDealTaskForm = false;
          this.resetDealTaskForm();
          this.resetTouchFollowUpForm();
          this.resetTaskFollowUpForm();
          this.taskTouchOptions = [];
          this.cancelSourceCreate();
          this.showDealCompanyForm = false;
          this.showDealContactsPanel = false;
          this.showDealDocumentsPanel = false;
          this.resetDealDocumentGeneratorState();
          this.showDealPhoneCallHistory = false;
          this.showLeadDocumentsPanel = false;
          this.showLeadPhoneCallHistory = false;
          this.resetDealCommunicationsState();
          this.showDealContactForm = false;
          this.resetDealCompanyForm();
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          this.dealDocumentsForActiveDeal = [];
          this.leadDocumentsForActiveLead = [];
          this.touchDealDocuments = [];
          this.touchCompanyDocuments = [];
          this.showCompanyContactForm = false;
          this.showCompanyContactsPanel = false;
          this.showCompanyDocumentsPanel = false;
          this.showCompanySettlementsPanel = false;
          this.showCompanyPhoneCallHistory = false;
          this.resetCompanyCommunicationsState();
          this.showCompanyRequisites = false;
          this.showCompanySettlementsPanel = false;
          this.showCompanyWorkRules = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyNoteDraft = false;
          this.showCompanyOkvedDetails = false;
          this.taskChecklistHideCompleted = false;
          this.resetCompanyContactForm();
          this.companyContactsForActiveCompany = [];
          this.companyDocumentsForActiveCompany = [];
          this.companyDealDocumentGroups = [];
          this.resetCompanySettlementState();
        },
        openCreateModal() {
          this.clearUiErrors({ modalOnly: true });
          this.leadSummaryEditingField = "";
          this.taskSummaryEditingField = "";
          this.companySummaryEditingField = "";
          this.showAllTouchResults = false;
          this.showDealCompanyFilter = false;
          this.showTouchCompanyFilter = false;
          this.showTouchDealFilter = false;
          this.closeDealDocumentSendSidebar();
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.resetExpandedOptionalFields();
          this.showCompanyNoteDraft = false;
          this.showCompanyRequisites = false;
          this.showCompanySettlementsPanel = false;
          this.showCompanyWorkRules = false;
          this.showCompanyContactsPanel = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showDealTaskForm = false;
          this.forms[this.activeSection] = this.getDefaultForm(this.activeSection);
          this.resetDealTaskForm();
          this.resetTouchFollowUpForm();
          this.resetTaskFollowUpForm();
          this.cancelSourceCreate();
          this.showDealCompanyForm = false;
          this.showDealContactsPanel = false;
          this.resetDealDocumentGeneratorState();
          this.resetDealCommunicationsState();
          this.showDealContactForm = false;
          this.resetDealCompanyForm();
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          this.touchDealDocuments = [];
          this.touchCompanyDocuments = [];
          this.showCompanyContactForm = false;
          this.showCompanyContactsPanel = false;
          this.showCompanySettlementsPanel = false;
          this.resetCompanyCommunicationsState();
          this.resetUnboundCommunicationsState();
          this.showCompanyWorkRules = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyOkvedDetails = false;
          this.taskChecklistHideCompleted = false;
          this.resetCompanyContactForm();
          this.companyContactsForActiveCompany = [];
          this.resetCompanySettlementState();
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
              websiteSessionId: "",
              events: ""
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
              telegram: "",
              whatsapp: "",
              maxContact: "",
              roleId: null,
              role: "",
              personNote: "",
              isPrimary: false
            };
          }
          if (section === "companies") {
            return {
              name: "",
              legalName: "",
              inn: "",
              companyType: "client",
              address: "",
              actualAddress: "",
              ogrn: "",
              kpp: "",
              bankDetails: "",
              settlementAccount: "",
              correspondentAccount: "",
              iban: "",
              bik: "",
              bankName: "",
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
              taskCategoryId: null,
              taskTypeId: null,
              communicationChannelId: null,
              priority: "medium",
              ownerId: this.currentUserId,
              companyId: null,
              leadId: null,
              dealId: null,
              relatedTouchId: null,
            dueAt: "",
            reminderOffsetMinutes: 30,
            checklist: [],
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
              resultOptionId: null,
              direction: "outgoing",
              summary: "",
              nextStep: "",
              nextStepAt: "",
              ownerId: null,
              companyId: null,
              contactId: null,
              taskId: null,
              leadId: null,
              dealId: null,
              dealDocumentIds: [],
              clientDocumentIds: [],
              documentUploadTarget: "",
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
        documentDisplayName(value, fallback = "Документ") {
          const normalized = String(value || "").trim();
          if (!normalized) {
            return fallback;
          }
          if (normalized.toLowerCase().endsWith(".docx")) {
            return normalized.slice(0, -5).trim() || fallback;
          }
          return normalized;
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
          const [leadStatuses, dealStages, leadSources, users, taskCategories, taskTypes, touchResults, outcomes, nextStepTemplates, automationRules, communicationChannels, contactRoles, contactStatuses] = await Promise.all([
            this.apiRequest("/api/v1/meta/lead-statuses/"),
            this.apiRequest("/api/v1/meta/deal-stages/"),
            this.apiRequest("/api/v1/meta/lead-sources/"),
            this.apiRequest("/api/v1/meta/users/"),
            this.apiRequest("/api/v1/meta/task-categories/"),
            this.apiRequest("/api/v1/meta/task-types/"),
            this.apiRequest("/api/v1/meta/touch-results/"),
            this.apiRequest("/api/v1/meta/outcomes/"),
            this.apiRequest("/api/v1/meta/next-step-templates/"),
            this.apiRequest("/api/v1/meta/automation-rules/"),
            this.apiRequest("/api/v1/meta/communication-channels/"),
            this.apiRequest("/api/v1/meta/contact-roles/"),
            this.apiRequest("/api/v1/meta/contact-statuses/")
          ]);
          this.metaOptions.leadStatuses = this.normalizePaginatedResponse(leadStatuses);
          this.metaOptions.dealStages = this.sortDealStages(this.normalizePaginatedResponse(dealStages));
          this.metaOptions.leadSources = this.normalizePaginatedResponse(leadSources);
          this.metaOptions.users = this.normalizePaginatedResponse(users);
          this.metaOptions.taskCategories = this.normalizePaginatedResponse(taskCategories);
          this.metaOptions.taskTypes = this.normalizePaginatedResponse(taskTypes);
          this.metaOptions.touchResults = this.normalizePaginatedResponse(touchResults);
          this.metaOptions.outcomes = this.normalizePaginatedResponse(outcomes);
          this.metaOptions.nextStepTemplates = this.normalizePaginatedResponse(nextStepTemplates);
          this.metaOptions.automationRules = this.normalizePaginatedResponse(automationRules);
          this.metaOptions.communicationChannels = this.normalizePaginatedResponse(communicationChannels);
          this.metaOptions.contactRoles = this.normalizePaginatedResponse(contactRoles);
          this.metaOptions.contactStatuses = this.normalizePaginatedResponse(contactStatuses);
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
          const currentDeal = (this.datasets.deals || []).find((item) => String(item.id) === String(targetDealId)) || null;
          const subject = this.resolveTaskSubject(this.dealTaskForm);
          if (!subject) {
            throw new Error("Укажите название задачи или выберите тип задачи");
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
                task_type: this.toIntOrNull(this.dealTaskForm.taskTypeId),
                communication_channel: this.taskFormUsesCommunicationChannel(this.dealTaskForm)
                  ? this.toIntOrNull(this.dealTaskForm.communicationChannelId)
                  : null,
                description: this.dealTaskForm.description.trim(),
                due_at: this.toIsoDateTime(this.dealTaskForm.dueAt),
                deadline_reminder_offset_minutes: Number(this.dealTaskForm.reminderOffsetMinutes || 30),
                deal: targetDealId,
                client: this.toIntOrNull(this.forms.deals.companyId) || this.toIntOrNull(currentDeal?.clientId),
                lead: this.toIntOrNull(currentDeal?.leadId)
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
                company_type: this.dealCompanyForm.companyType || "client",
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
                telegram: form.telegram.trim(),
                whatsapp: form.whatsapp.trim(),
                max_contact: form.maxContact.trim(),
                role: this.toIntOrNull(form.roleId),
                person_note: form.personNote.trim(),
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
                telegram: form.telegram.trim(),
                whatsapp: form.whatsapp.trim(),
                max_contact: form.maxContact.trim(),
                role: this.toIntOrNull(form.roleId),
                person_note: form.personNote.trim(),
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
              company_type: form.companyType || "client",
              address: form.address.trim(),
              actual_address: form.actualAddress.trim(),
              ogrn: form.ogrn.trim(),
              kpp: form.kpp.trim(),
              bank_details: form.bankDetails.trim(),
              settlement_account: form.settlementAccount.trim(),
              correspondent_account: form.correspondentAccount.trim(),
              iban: form.iban.trim(),
              bik: form.bik.trim(),
              bank_name: form.bankName.trim(),
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
              company_type: form.companyType || "client",
              address: form.address.trim(),
              actual_address: form.actualAddress.trim(),
              ogrn: form.ogrn.trim(),
              kpp: form.kpp.trim(),
              bank_details: form.bankDetails.trim(),
              settlement_account: form.settlementAccount.trim(),
              correspondent_account: form.correspondentAccount.trim(),
              iban: form.iban.trim(),
              bik: form.bik.trim(),
              bank_name: form.bankName.trim(),
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
                telegram: this.companyContactForm.telegram.trim(),
                whatsapp: this.companyContactForm.whatsapp.trim(),
                max_contact: this.companyContactForm.maxContact.trim(),
                role: this.toIntOrNull(this.companyContactForm.roleId),
                person_note: this.companyContactForm.personNote.trim(),
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
          const subject = this.resolveTaskSubject(form);
          if (!subject) {
            throw new Error("Укажите название задачи или выберите тип задачи");
          }
          if (!form.dueAt) {
            throw new Error("Укажите срок задачи");
          }
          if (form.saveCompanyNote && !form.companyNote.trim()) {
            throw new Error("Укажите важные факты о компании");
          }
          this.validateTaskCompletionEvidence(form);
          this.validateTaskFollowUpRequirement();
          const clientId = this.toIntOrNull(form.companyId);
          const communicationChannelId = this.taskFormUsesCommunicationChannel(form)
            ? this.toIntOrNull(form.communicationChannelId)
            : null;
          const ownerId = this.toIntOrNull(form.ownerId) || this.currentUserId;
          await this.apiRequest("/api/v1/activities/", {
            method: "POST",
            body: {
              type: "task",
              subject,
              owner: ownerId,
              task_type: this.toIntOrNull(form.taskTypeId),
              communication_channel: communicationChannelId,
              priority: form.priority || "medium",
              description: form.description.trim(),
              checklist: this.serializeTaskChecklist(form.checklist),
              result: form.result.trim(),
              due_at: this.toIsoDateTime(form.dueAt),
              deadline_reminder_offset_minutes: Number(form.reminderOffsetMinutes || 30),
              client: clientId,
              lead: this.toIntOrNull(form.leadId),
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
          const subject = this.resolveTaskSubject(form);
          if (!subject) {
            throw new Error("Укажите название задачи или выберите тип задачи");
          }
          if (!form.dueAt) {
            throw new Error("Укажите срок задачи");
          }
          if (form.saveCompanyNote && !form.companyNote.trim()) {
            throw new Error("Укажите важные факты о компании");
          }
          this.validateTaskCompletionEvidence(form);
          this.validateTaskFollowUpRequirement();
          const clientId = this.toIntOrNull(form.companyId);
          const communicationChannelId = this.taskFormUsesCommunicationChannel(form)
            ? this.toIntOrNull(form.communicationChannelId)
            : null;
          const ownerId = this.toIntOrNull(form.ownerId) || this.currentUserId;
          await this.apiRequest(`/api/v1/activities/${this.editingTaskId}/`, {
            method: "PATCH",
            body: {
              type: "task",
              subject,
              owner: ownerId,
              task_type: this.toIntOrNull(form.taskTypeId),
              communication_channel: communicationChannelId,
              priority: form.priority || "medium",
              description: form.description.trim(),
              checklist: this.serializeTaskChecklist(form.checklist),
              result: form.result.trim(),
              due_at: this.toIsoDateTime(form.dueAt),
              deadline_reminder_offset_minutes: Number(form.reminderOffsetMinutes || 30),
              client: clientId,
              lead: this.toIntOrNull(form.leadId),
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
          if (this.hasPreparedTouchFollowUp() && !this.hasValidTouchFollowUp()) {
            throw new Error("Для следующей задачи укажите название или тип задачи и срок");
          }
          const selectedResult = (this.metaOptions.touchResults || []).find(
            (option) => String(option.id) === String(this.toIntOrNull(form.resultOptionId) || "")
          );
          const availableResultIds = this.availableTouchResults(form.channelId, form.resultOptionId).map((option) => String(option.id));
          if (selectedResult && !availableResultIds.includes(String(selectedResult.id))) {
            throw new Error(`Результат "${selectedResult.name}" нельзя использовать с выбранным типом канала`);
          }
          this.validateTouchNextActivityRequirement(form);
        },
        validateTouchNextActivityRequirement(form) {
          const dealId = this.toIntOrNull(form.dealId);
          if (!dealId) {
            return;
          }
          const deal = (this.datasets.deals || []).find((item) => String(item.id) === String(dealId));
          const stageCode = String(deal?.stageCode || "").trim().toLowerCase();
          if (stageCode === "won" || stageCode === "failed") {
            return;
          }

          const now = Date.now();
          const currentNextStepAt = this.parseTaskDueTimestamp(this.toIsoDateTime(form.nextStepAt));
          if (currentNextStepAt !== null && currentNextStepAt >= now) {
            return;
          }
          if (this.hasValidTouchFollowUp()) {
            return;
          }

          const hasFutureTouch = (this.datasets.touches || []).some((touch) => {
            if (String(touch.dealId || "") !== String(dealId)) {
              return false;
            }
            if (this.editingTouchId && String(touch.id) === String(this.editingTouchId)) {
              return false;
            }
            const nextStepAt = this.parseTaskDueTimestamp(touch.nextStepAtRaw);
            return nextStepAt !== null && nextStepAt >= now;
          });
          if (hasFutureTouch) {
            return;
          }

          const hasActiveTask = (this.datasets.tasks || []).some((task) => (
            String(task.dealId || "") === String(dealId)
            && this.isTaskActiveStatus(task.taskStatus || task.status)
            && !this.isTaskOverdue(task.dueAtRaw, task.taskStatus || task.status)
          ));
          if (hasActiveTask) {
            return;
          }

          throw new Error("После касания по активной сделке укажите дату следующего шага, создайте задачу или закройте сделку");
        },
        async createTouch() {
          const form = this.forms.touches;
          this.validateTouchForm(form);
          const followUpSubject = this.resolveTaskSubject(this.touchFollowUpForm);
          const nextStepText = followUpSubject || form.nextStep.trim();
          const nextStepAtValue = this.touchFollowUpForm.dueAt || form.nextStepAt;
          return this.apiRequest("/api/v1/touches/", {
            method: "POST",
            body: {
              happened_at: this.toIsoDateTime(form.happenedAt),
              channel: this.toIntOrNull(form.channelId),
              result_option: this.toIntOrNull(form.resultOptionId),
              direction: form.direction || "outgoing",
              summary: form.summary.trim(),
              next_step: nextStepText,
              next_step_at: this.toIsoDateTime(nextStepAtValue),
              owner: this.toIntOrNull(form.ownerId),
              client: this.toIntOrNull(form.companyId),
              contact: this.toIntOrNull(form.contactId),
              task: this.toIntOrNull(form.taskId),
              lead: this.toIntOrNull(form.leadId),
              deal: this.toIntOrNull(form.dealId),
              deal_document_ids: (form.dealDocumentIds || []).map((id) => this.toIntOrNull(id)).filter(Boolean),
              client_document_ids: (form.clientDocumentIds || []).map((id) => this.toIntOrNull(id)).filter(Boolean),
              has_follow_up_task: this.hasValidTouchFollowUp(),
            }
          });
        },
        async updateTouch() {
          const form = this.forms.touches;
          if (!this.editingTouchId) {
            throw new Error("Касание для редактирования не выбрано");
          }
          this.validateTouchForm(form);
          const followUpSubject = this.resolveTaskSubject(this.touchFollowUpForm);
          const nextStepText = followUpSubject || form.nextStep.trim();
          const nextStepAtValue = this.touchFollowUpForm.dueAt || form.nextStepAt;
          return this.apiRequest(`/api/v1/touches/${this.editingTouchId}/`, {
            method: "PATCH",
            body: {
              happened_at: this.toIsoDateTime(form.happenedAt),
              channel: this.toIntOrNull(form.channelId),
              result_option: this.toIntOrNull(form.resultOptionId),
              direction: form.direction || "outgoing",
              summary: form.summary.trim(),
              next_step: nextStepText,
              next_step_at: this.toIsoDateTime(nextStepAtValue),
              owner: this.toIntOrNull(form.ownerId),
              client: this.toIntOrNull(form.companyId),
              contact: this.toIntOrNull(form.contactId),
              task: this.toIntOrNull(form.taskId),
              lead: this.toIntOrNull(form.leadId),
              deal: this.toIntOrNull(form.dealId),
              deal_document_ids: (form.dealDocumentIds || []).map((id) => this.toIntOrNull(id)).filter(Boolean),
              client_document_ids: (form.clientDocumentIds || []).map((id) => this.toIntOrNull(id)).filter(Boolean),
              has_follow_up_task: this.hasValidTouchFollowUp(),
            }
          });
        },
        async createFollowUpTaskFromCurrentDeal() {
          const followUp = this.taskFollowUpForm;
          const subject = this.resolveTaskSubject(followUp);
          if (!subject || !followUp.dueAt) {
            return;
          }
          const dealId = this.toIntOrNull(this.forms.tasks.dealId);
          const clientId = this.toIntOrNull(this.forms.tasks.companyId);
          await this.apiRequest("/api/v1/activities/", {
            method: "POST",
              body: {
                type: "task",
                subject,
                task_type: this.toIntOrNull(followUp.taskTypeId),
                communication_channel: this.taskFormUsesCommunicationChannel(followUp)
                  ? this.toIntOrNull(followUp.communicationChannelId)
                  : null,
              description: followUp.description.trim(),
              due_at: this.toIsoDateTime(followUp.dueAt),
              deadline_reminder_offset_minutes: Number(followUp.reminderOffsetMinutes || 30),
              client: clientId,
              deal: dealId,
              status: "todo"
            }
          });
        },
        async createFollowUpTaskFromCurrentTouch(touchId = null) {
          const followUp = this.touchFollowUpForm;
          const subject = this.resolveTaskSubject(followUp);
          if (!subject || !followUp.dueAt) {
            return;
          }
          await this.apiRequest("/api/v1/activities/", {
            method: "POST",
              body: {
                type: "task",
                subject,
                task_type: this.toIntOrNull(followUp.taskTypeId),
                communication_channel: this.taskFormUsesCommunicationChannel(followUp)
                  ? this.toIntOrNull(followUp.communicationChannelId)
                  : null,
              description: followUp.description.trim(),
              due_at: this.toIsoDateTime(followUp.dueAt),
              deadline_reminder_offset_minutes: Number(followUp.reminderOffsetMinutes || 30),
              client: this.toIntOrNull(this.forms.touches.companyId),
              deal: this.toIntOrNull(this.forms.touches.dealId),
              lead: this.toIntOrNull(this.forms.touches.leadId),
              contact: this.toIntOrNull(this.forms.touches.contactId),
              related_touch: this.toIntOrNull(touchId),
              status: "todo"
            }
          });
        },
        async createItem() {
          this.isSaving = true;
          this.clearUiErrors({ modalOnly: true });
          try {
            const returnToParentAfterChildModal = (this.activeSection === "touches" || this.activeSection === "tasks") && !!this.modalParentContext;
            let savedDeal = null;
            const currentTouchId = this.editingTouchId;
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
            if (this.activeSection === "tasks" && this.editingTaskId && this.showTaskFollowUpSuggestion && this.hasPreparedTaskFollowUp()) {
              await this.createFollowUpTaskFromCurrentDeal();
            }
            if (this.activeSection === "tasks" && !this.editingTaskId) await this.createTask();
            let savedTouch = null;
            if (this.activeSection === "touches" && currentTouchId) savedTouch = await this.updateTouch();
            if (this.activeSection === "touches" && !currentTouchId) savedTouch = await this.createTouch();
            if (this.activeSection === "touches" && this.hasValidTouchFollowUp()) {
              await this.createFollowUpTaskFromCurrentTouch(savedTouch && savedTouch.id ? savedTouch.id : currentTouchId);
            }
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
            this.resetTouchFollowUpForm();
            this.resetTaskFollowUpForm();
            this.showDealCompanyForm = false;
            this.resetDealCompanyForm();
            this.dealTasksForActiveDeal = [];
            this.showCompanyContactForm = false;
            this.showCompanyContactsPanel = false;
            this.showCompanyWorkRules = false;
            this.showCompanyDealsPanel = false;
            this.showCompanyLeadsPanel = false;
            this.resetCompanyContactForm();
            this.companyContactsForActiveCompany = [];
            if (this.activeSection === "leads") {
              await Promise.all([this.loadSection("leads"), this.loadSection("deals"), this.loadAutomationDrafts(), this.loadAutomationQueue(), this.loadAutomationMessageDrafts()]);
            } else if (this.activeSection === "deals") {
              await Promise.all([this.loadSection("deals"), this.loadSection("companies"), this.loadAutomationDrafts(), this.loadAutomationQueue(), this.loadAutomationMessageDrafts()]);
            } else if (this.activeSection === "tasks") {
              await Promise.all([this.loadSection("tasks"), this.loadSection("deals"), this.loadSection("companies"), this.loadAutomationDrafts(), this.loadAutomationQueue(), this.loadAutomationMessageDrafts()]);
            } else if (this.activeSection === "touches") {
              await Promise.all([this.loadSection("touches"), this.loadSection("leads"), this.loadSection("deals"), this.loadSection("companies"), this.loadAutomationDrafts(), this.loadAutomationQueue(), this.loadAutomationMessageDrafts()]);
            } else {
              await this.reloadActiveSection();
            }
            if (returnToParentAfterChildModal) {
              await this.restoreModalParentContext();
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
        if (
          savedSection
          && (
            Object.prototype.hasOwnProperty.call(SECTION_ENDPOINTS, savedSection)
            || savedSection === "telephony"
            || savedSection === "communications"
          )
        ) {
          this.activeSection = savedSection;
        }
        try {
          await this.loadMetaOptions();
        } catch (error) {
          this.errorMessage = `Ошибка загрузки справочников: ${error.message}`;
        }
        await this.loadAllSections();
        this.isSectionLazyLoadingReady = true;
        if (this.activeSection === "telephony") {
          try {
            await this.loadTelephonySettings();
          } catch (error) {
            this.errorMessage = `Ошибка загрузки телефонии: ${error.message}`;
          }
        } else if (this.activeSection === "communications") {
          try {
            await this.loadCommunicationsCompanies();
          } catch (error) {
            this.errorMessage = `Ошибка загрузки коммуникаций: ${error.message}`;
          }
        }
        this.ensureTelephonyIncomingCallsPolling();
        this.restoreFilters();
        window.setTimeout(() => this.hideStartupScreen(), 500);
      },
      beforeUnmount() {
        document.removeEventListener("click", this.handleDocumentClick);
        document.removeEventListener("keydown", this.handleGlobalKeydown);
        this.stopTelephonyIncomingCallsPolling();
        this.stopAutomationNotificationsPolling();
        this.stopCommunicationsPollingIfIdle();
      }
    });

    app.config.compilerOptions.delimiters = ["[[", "]]"];
    app.mount("#app");
