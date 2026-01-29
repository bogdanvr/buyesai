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
            isSendingDiscuss: false,
            discussSent: false,

        };
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
    
        
        async submitHeroForm() {
            this.isSending = true;
            try {
                // здесь будет реальный POST на Django
                console.log('Отправка:', {
                    name: this.name,
                    phone: this.phone,
                    company: this.company,
                    direction: this.direction,
                });
                // имитация задержки
                await new Promise(r => setTimeout(r, 500));
                this.sent = true;
            } finally {
                this.isSending = false;
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