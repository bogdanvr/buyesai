    const { createApp } = Vue;
    const appRootElement = document.getElementById("app");
    const appRootTemplate = appRootElement ? String(appRootElement.innerHTML || "") : "";

    const SECTION_ENDPOINTS = {
      leads: "/api/v1/leads/?page_size=100",
      deals: "/api/v1/deals/?page_size=100",
      contacts: "/api/v1/contacts/?page_size=100",
      companies: "/api/v1/clients/?page_size=100",
      tasks: "/api/v1/activities/?type=task&page_size=100",
      touches: "/api/v1/touches/?page_size=100"
    };
    const FILTERS_STORAGE_KEY = "crm_section_filters";

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
          modalParentContext: null,
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
          selectedStatusFilters: [],
          statusFiltersBySection: {
            leads: [],
            deals: [],
            contacts: [],
            companies: [],
            tasks: [],
            touches: [],
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
          showDealContactForm: false,
          isDealContactsLoading: false,
          isDealDocumentsLoading: false,
          isDealCommunicationsLoading: false,
          isDealConversationMessagesLoading: false,
          isDealCommunicationSending: false,
          isDealCommunicationStarting: false,
          isDealDocumentUploading: false,
          isTouchDocumentsLoading: false,
          isTouchDocumentUploading: false,
          touchResultPromptVisible: false,
          touchResultPromptText: "",
          showAllTouchResults: false,
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
          showCompanyNoteDraft: false,
          showCompanyOkvedDetails: false,
          showCompanyRequisites: false,
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
              address: "",
              actualAddress: "",
              bankDetails: "",
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
          leadDocumentsForActiveLead: [],
          dealCommunications: [],
          dealManualBindingConversations: [],
          dealConversationMessages: [],
          activeDealConversationId: null,
          showDealCommunicationStartForm: false,
          dealCommunicationComposer: {
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
            touches: [],
            automationDrafts: [],
            automationQueue: [],
            automationMessageDrafts: []
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
            conversationId: this.toIntOrNull(item.conversationId),
            dealId: this.toIntOrNull(item.dealId),
            dealTitle: item.dealTitle || "",
            companyId: this.toIntOrNull(item.clientId),
            companyName: item.clientName || "",
            leadId: this.toIntOrNull(item.leadId),
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
          if (this.dealAutomationNextAction?.title) {
            return this.dealAutomationNextAction.title;
          }
          return this.dealSummaryNextStepTask?.subject || this.dealSummaryNextTouch?.nextStep || "Не указан";
        },
        dealSummaryNextStepAtLabel() {
          if (this.dealAutomationNextAction?.at) {
            return this.formatDueLabel(this.dealAutomationNextAction.at);
          }
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
        dealTimelineItems() {
          return this.groupDealTimelineEvents(this.parsedDealEventItems);
        },
        parsedLeadEventItems() {
          return this.parseEventLog(this.leadEventLog(this.forms.leads));
        },
        leadTimelineItems() {
          return this.groupDealTimelineEvents(this.parsedLeadEventItems);
        },
        parsedCompanyEventItems() {
          return this.parseEventLog(this.forms.companies.events);
        },
        companyTimelineItems() {
          return this.groupDealTimelineEvents(this.parsedCompanyEventItems);
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
        activeFilterRows() {
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
        filteredItems() {
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
        },
        filteredTaskTypeOptions() {
          return this.filterTaskTypesByCategory(this.forms.tasks.taskCategoryId);
        },
        filteredTaskCategoryOptions() {
          return this.filterTaskCategories();
        }
      },
      watch: {
        activeSection(nextValue, previousValue) {
          this.syncStatusFiltersForSection(previousValue);
          this.applyStatusFiltersForSection(nextValue);
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
            if (this.toIntOrNull(this.forms.tasks.dealId)) {
              this.forms.tasks.leadId = null;
            }
            if (this.activeSection === "tasks" && this.showModal) {
              this.loadTaskTouchOptions();
            }
          }
        },
        "forms.tasks.leadId": {
          handler(nextValue) {
            if (this.toIntOrNull(nextValue)) {
              this.forms.tasks.companyId = null;
              this.forms.tasks.dealId = null;
            }
            if (this.activeSection === "tasks" && this.showModal) {
              this.loadTaskTouchOptions();
            }
          }
        },
        "forms.tasks.companyId": {
          handler() {
            if (this.toIntOrNull(this.forms.tasks.companyId)) {
              this.forms.tasks.leadId = null;
            }
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
              }
              this.loadTouchDocuments();
            }
            this.applyTouchOwnerFromContext();
          }
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
        resizeTextareaById(id) {
          const element = document.getElementById(id);
          if (!element) return;
          element.style.height = "0px";
          element.style.height = `${Math.max(element.scrollHeight, 44)}px`;
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
        emailHref(value) {
          const normalized = String(value || "").trim();
          return normalized ? `mailto:${normalized}` : "";
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
            const company = (this.datasets.companies || []).find((item) => String(item.id) === String(companyId));
            if (company) {
              this.openCompanyEditor(company);
              this.showCompanyCommunicationsPanel = true;
              await this.loadCompanyCommunications({ preserveSelection: false, forceReloadMessages: true });
              await this.selectCompanyConversation(conversationId, { silent: true });
              this.ensureCommunicationsPolling();
              return;
            }
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
        closeCompanyPanels(exceptKey = "") {
          const normalized = String(exceptKey || "");
          this.showCompanyRequisites = normalized === "requisites" ? this.showCompanyRequisites : false;
          this.showCompanyContactsPanel = normalized === "contacts" ? this.showCompanyContactsPanel : false;
          this.showCompanyDocumentsPanel = normalized === "documents" ? this.showCompanyDocumentsPanel : false;
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
            : normalized === "contacts"
              ? this.showCompanyContactsPanel
              : normalized === "documents"
                ? this.showCompanyDocumentsPanel
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
          if (normalized === "contacts") this.showCompanyContactsPanel = true;
          if (normalized === "documents") this.showCompanyDocumentsPanel = true;
          if (normalized === "communications") this.showCompanyCommunicationsPanel = true;
          if (normalized === "workRules") this.showCompanyWorkRules = true;
          if (normalized === "deals") this.showCompanyDealsPanel = true;
          if (normalized === "leads") this.showCompanyLeadsPanel = true;
        },
        toggleCompanyRequisites() {
          this.toggleExclusiveCompanyPanel("requisites");
        },
        toggleCompanyWorkRules() {
          this.toggleExclusiveCompanyPanel("workRules");
        },
        async toggleCompanyDocumentsPanel() {
          const wasOpen = this.showCompanyDocumentsPanel;
          this.toggleExclusiveCompanyPanel("documents");
          if (!wasOpen && this.showCompanyDocumentsPanel) {
            await this.loadCompanyDocuments();
          }
        },
        async toggleCompanyCommunicationsPanel() {
          const wasOpen = this.showCompanyCommunicationsPanel;
          this.toggleExclusiveCompanyPanel("communications");
          if (!wasOpen && this.showCompanyCommunicationsPanel) {
            await this.loadCompanyCommunications({ preserveSelection: false });
            return;
          }
          if (!this.showCompanyCommunicationsPanel) {
            this.stopCommunicationsPollingIfIdle();
          }
        },
        toggleCompanyDealsPanel() {
          this.toggleExclusiveCompanyPanel("deals");
        },
        toggleCompanyLeadsPanel() {
          this.toggleExclusiveCompanyPanel("leads");
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
          if (!tasks.length) {
            this.stopCommunicationsPollingIfIdle();
            return;
          }
          await Promise.all(tasks);
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
          const hasBody = options.body !== undefined;
          const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
          if (hasBody) {
            headers["X-CSRFToken"] = this.getCsrfToken();
            if (!isFormData) {
              headers["Content-Type"] = "application/json";
            }
          }
          const response = await fetch(url, {
            method: options.method || "GET",
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
            if (actionId === "reply" && notification?.isPrimaryMessage) {
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
        managerNotificationReplyState(notification) {
          const queueId = this.toIntOrNull(notification?.sourceId);
          if (!queueId) return "";
          return String(this.managerNotificationReplyStates[String(queueId)] || "").trim();
        },
        managerNotificationReplyButtonVisible(notification) {
          if (String(notification?.sourceType || "") !== "queue") return false;
          if (String(notification?.queueKind || "") === "next_step") return false;
          if (this.managerNotificationReplyState(notification) === "answered") return true;
          return !!this.toIntOrNull(notification?.messageDraftId);
        },
        managerNotificationReplyButtonLabel(notification) {
          return this.managerNotificationReplyState(notification) === "answered" ? "Отвечено" : "Ответить";
        },
        managerNotificationReplyButtonDisabled(notification) {
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
            companyId: this.toIntOrNull(item?.clientId || item?.companyId),
            dealId: normalizedDealId,
            // `related_touch` in the activities API points to legacy Activity entries,
            // while automation notifications are sourced from Touch records.
            // Passing Touch ids here breaks task creation with a validation error.
            relatedTouchId: null,
            dueAt: resolvedDueAt ? this.toDateTimeLocal(resolvedDueAt) : "",
            reminderOffsetMinutes: 30,
            description: "",
            result: "",
            saveCompanyNote: false,
            companyNote: "",
            status: "todo",
          };
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
          const normalizedDraftId = this.toIntOrNull(messageDraftId);
          if (!normalizedDraftId) {
            this.setUiError("Не найдено сообщение для ответа.", { modal: true });
            return;
          }
          const draft = this.getAutomationMessageDraftById(normalizedDraftId);
          if (!draft) {
            this.setUiError("Черновик ответа не найден. Обновите уведомления и попробуйте снова.", { modal: true });
            return;
          }
          const conversationId = this.toIntOrNull(draft?.conversationId) || this.toIntOrNull(this.activeUnboundConversationId);
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
              await this.apiRequest(`/api/v1/automation-message-drafts/${draft.id}/dismiss/`, {
                method: "POST",
                body: {},
              });
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
            if (!allowedTypes.length || !selectedChannelCode) {
            } else if (!allowedTypes.includes(selectedChannelCode)) {
              return false;
            }
            if (normalizedChannelId && channelTouchResultIds.length && !channelTouchResultIds.includes(optionId)) {
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
        persistFilters() {
          this.syncStatusFiltersForSection(this.activeSection);
          try {
            window.localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify({
              statusFiltersBySection: this.statusFiltersBySection,
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
            if (Array.isArray(payload?.selectedStatusFilters)) {
              normalizedStatusFilters[this.activeSection] = payload.selectedStatusFilters
                .map((item) => String(item || "").trim())
                .filter(Boolean);
            }
            this.statusFiltersBySection = normalizedStatusFilters;
            this.applyStatusFiltersForSection(this.activeSection);
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
        openDealEditorById(dealId) {
          const normalizedId = this.toIntOrNull(dealId);
          if (!normalizedId) return;
          const deal = (this.datasets.deals || []).find((item) => String(item.id) === String(normalizedId));
          if (deal) {
            this.openDealEditor(deal);
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
        },
        openCompanyEditor(item) {
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
          this.resetCompanyCommunicationsState();
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyNoteDraft = false;
          this.companyDocumentsForActiveCompany = [];
          this.companyDealDocumentGroups = [];
          this.resetExpandedOptionalFields();
          const normalizedOkveds = this.normalizeCompanyOkveds(item.okveds, item.okved, item.industry);
          const resolvedIndustry = this.resolvePrimaryIndustry(item.industry, item.okved, normalizedOkveds);
          this.forms.companies = {
            name: item.name || "",
            legalName: item.legalName || "",
            inn: item.inn || "",
            address: item.address || "",
            actualAddress: item.actualAddress || "",
            bankDetails: item.bankDetails || "",
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
          this.resetCompanyCommunicationsState();
          this.showCompanyWorkRules = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.loadContactsForCompany();
          this.showModal = true;
          this.enrichCompanyFromDadataByInn();
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
            companyId: this.toIntOrNull(item.clientId),
            leadId: this.toIntOrNull(item.leadId),
            dealId: this.toIntOrNull(item.dealId),
            relatedTouchId: this.toIntOrNull(item.relatedTouchId),
            dueAt: this.toDateTimeLocal(item.dueAtRaw),
            reminderOffsetMinutes: Number(item.reminderOffsetMinutes || 30),
            description: item.description || "",
            result: item.result || this.resolveTaskTypeDefaultResultById(item.taskTypeId),
            saveCompanyNote: !!item.saveCompanyNote,
            companyNote: item.companyNote || "",
            status: item.taskStatus || item.status || "todo"
          };
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
              showDealContactForm: !!this.showDealContactForm,
            };
          }
          if (this.activeSection === "leads" && this.toIntOrNull(this.editingLeadId)) {
            return {
              section: "leads",
              editingLeadId: this.toIntOrNull(this.editingLeadId),
              leadSummaryEditingField: String(this.leadSummaryEditingField || ""),
              showLeadDocumentsPanel: !!this.showLeadDocumentsPanel,
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
            return true;
          }
          if (context.section === "leads") {
            this.editingDealId = null;
            this.editingLeadId = this.toIntOrNull(context.editingLeadId);
            this.leadSummaryEditingField = String(context.leadSummaryEditingField || "");
            this.showLeadDocumentsPanel = !!context.showLeadDocumentsPanel;
            if (this.showLeadDocumentsPanel) {
              await this.loadLeadDocuments();
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
          this.forms.touches = {
            happenedAt: this.toDateTimeLocal(item.happenedAtRaw),
            channelId: this.toIntOrNull(item.channelId),
            resultOptionId: this.toIntOrNull(item.resultOptionId),
            direction: item.direction || "outgoing",
            summary: item.summary || "",
            nextStep: item.nextStep || "",
            nextStepAt: this.toDateTimeLocal(item.nextStepAtRaw),
            ownerId: this.toIntOrNull(item.ownerId),
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
            this.stopCommunicationsPollingIfIdle();
            await this.loadContactsForSelectedDealCompany();
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
            await this.loadDealCommunications({ preserveSelection: false });
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
        formatFileSize(bytes) {
          const size = Number.parseInt(bytes, 10);
          if (!Number.isFinite(size) || size <= 0) return "0 Б";
          if (size < 1024) return `${size} Б`;
          if (size < 1024 * 1024) return `${(size / 1024).toFixed(1).replace(".0", "")} КБ`;
          return `${(size / (1024 * 1024)).toFixed(1).replace(".0", "")} МБ`;
        },
        mapDealDocument(item) {
          return {
            id: item.id,
            scope: "deal",
            dealId: this.toIntOrNull(item.deal),
            originalName: item.original_name || item.originalName || "",
            fileUrl: item.download_url || item.downloadUrl || item.file_url || item.fileUrl || "",
            fileSize: Number.parseInt(item.file_size || item.fileSize || 0, 10) || 0,
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
            return;
          }
          this.isCompanyDocumentsLoading = true;
          try {
            const [companyPayload] = await Promise.all([
              this.apiRequest(`/api/v1/client-documents/?client=${companyId}&page_size=100`),
            ]);
            const companyRecords = Array.isArray(companyPayload?.results) ? companyPayload.results : (Array.isArray(companyPayload) ? companyPayload : []);
            this.companyDocumentsForActiveCompany = companyRecords.map((item) => this.mapClientDocument(item));

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
            this.stopCommunicationsPollingIfIdle();
            await this.loadDealDocuments();
          }
        },
        openDealDocumentPicker() {
          if (!this.editingDealId || this.isDealDocumentUploading) {
            return;
          }
          const input = this.$refs.dealDocumentInput;
          if (input) {
            input.click();
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
        async toggleLeadDocumentsPanel() {
          this.showLeadDocumentsPanel = !this.showLeadDocumentsPanel;
          if (this.showLeadDocumentsPanel) {
            await this.loadLeadDocuments();
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
            address: item.address || "",
            actualAddress: item.actual_address || "",
            bankDetails: item.bank_details || "",
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
            description: item.description || "",
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
            await Promise.all(
              Object.keys(SECTION_ENDPOINTS).map((section) => this.loadSection(section))
            );
            await Promise.all([this.loadAutomationDrafts(), this.loadAutomationQueue(), this.loadAutomationMessageDrafts()]);
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
            await Promise.all([this.loadAutomationDrafts(), this.loadAutomationQueue(), this.loadAutomationMessageDrafts()]);
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
          this.showLeadDocumentsPanel = false;
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
          this.resetCompanyCommunicationsState();
          this.showCompanyRequisites = false;
          this.showCompanyWorkRules = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyOkvedDetails = false;
          this.resetCompanyContactForm();
          this.companyContactsForActiveCompany = [];
          this.companyDocumentsForActiveCompany = [];
          this.companyDealDocumentGroups = [];
          if (!this.datasets[section].length) {
            this.reloadActiveSection();
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
          this.showLeadDocumentsPanel = false;
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
          this.resetCompanyCommunicationsState();
          this.showCompanyRequisites = false;
          this.showCompanyWorkRules = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyNoteDraft = false;
          this.showCompanyOkvedDetails = false;
          this.resetCompanyContactForm();
          this.companyContactsForActiveCompany = [];
          this.companyDocumentsForActiveCompany = [];
          this.companyDealDocumentGroups = [];
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
          this.editingLeadId = null;
          this.editingDealId = null;
          this.editingContactId = null;
          this.editingCompanyId = null;
          this.editingTaskId = null;
          this.editingTouchId = null;
          this.resetExpandedOptionalFields();
          this.showCompanyNoteDraft = false;
          this.showCompanyRequisites = false;
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
          this.resetDealCommunicationsState();
          this.showDealContactForm = false;
          this.resetDealCompanyForm();
          this.dealCompanyContacts = [];
          this.dealTasksForActiveDeal = [];
          this.touchDealDocuments = [];
          this.touchCompanyDocuments = [];
          this.showCompanyContactForm = false;
          this.showCompanyContactsPanel = false;
          this.resetCompanyCommunicationsState();
          this.resetUnboundCommunicationsState();
          this.showCompanyWorkRules = false;
          this.showCompanyDealsPanel = false;
          this.showCompanyLeadsPanel = false;
          this.showCompanyLeadsPanel = false;
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
              address: "",
              actualAddress: "",
              bankDetails: "",
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
              companyId: null,
              leadId: null,
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
              address: form.address.trim(),
              actual_address: form.actualAddress.trim(),
              bank_details: form.bankDetails.trim(),
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
              address: form.address.trim(),
              actual_address: form.actualAddress.trim(),
              bank_details: form.bankDetails.trim(),
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
          await this.apiRequest("/api/v1/activities/", {
            method: "POST",
            body: {
              type: "task",
              subject,
              task_type: this.toIntOrNull(form.taskTypeId),
              communication_channel: communicationChannelId,
              priority: form.priority || "medium",
              description: form.description.trim(),
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
          await this.apiRequest(`/api/v1/activities/${this.editingTaskId}/`, {
            method: "PATCH",
            body: {
              type: "task",
              subject,
              task_type: this.toIntOrNull(form.taskTypeId),
              communication_channel: communicationChannelId,
              priority: form.priority || "medium",
              description: form.description.trim(),
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
        if (savedSection && Object.prototype.hasOwnProperty.call(SECTION_ENDPOINTS, savedSection)) {
          this.activeSection = savedSection;
        }
        try {
          await this.loadMetaOptions();
        } catch (error) {
          this.errorMessage = `Ошибка загрузки справочников: ${error.message}`;
        }
        await this.loadAllSections();
        this.restoreFilters();
        window.setTimeout(() => this.hideStartupScreen(), 500);
      },
      beforeUnmount() {
        document.removeEventListener("click", this.handleDocumentClick);
        document.removeEventListener("keydown", this.handleGlobalKeydown);
      }
    });

    app.config.compilerOptions.delimiters = ["[[", "]]"];
    app.mount("#app");
