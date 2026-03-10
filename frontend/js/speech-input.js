/** 语音输入功能 */
class SpeechInput {
    constructor(inputElement, statusElement, iconElement) {
        this.input = inputElement;
        this.status = statusElement;
        this.icon = iconElement;
        this.recognition = null;
        this.isRecording = false;
        
        this.init();
    }
    
    init() {
        // 检查浏览器支持
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            this.icon.style.display = 'none';
            return;
        }
        
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'zh-CN';
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        
        this.recognition.onstart = () => {
            this.isRecording = true;
            this.icon.textContent = '🔴';
            this.status.textContent = '正在录音...';
            this.status.className = 'voice-status recording';
        };
        
        this.recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            this.input.value = transcript;
            
            if (event.results[event.resultIndex].isFinal) {
                this.status.textContent = '识别完成';
                this.status.className = 'voice-status';
            } else {
                this.status.textContent = '正在识别...';
                this.status.className = 'voice-status recognizing';
            }
        };
        
        this.recognition.onerror = (event) => {
            this.isRecording = false;
            this.icon.textContent = '🎤';
            this.status.className = 'voice-status';
            
            if (event.error === 'no-speech') {
                this.status.textContent = '未检测到语音，请重试';
            } else if (event.error === 'not-allowed') {
                this.status.textContent = '麦克风权限被拒绝，请在浏览器设置中允许';
            } else {
                this.status.textContent = `识别错误：${event.error}`;
            }
        };
        
        this.recognition.onend = () => {
            this.isRecording = false;
            this.icon.textContent = '🎤';
            if (this.status.textContent === '正在录音...') {
                this.status.textContent = '';
                this.status.className = 'voice-status';
            }
        };
    }
    
    toggle() {
        if (!this.recognition) {
            alert('您的浏览器不支持语音识别功能');
            return;
        }
        
        if (this.isRecording) {
            this.stop();
        } else {
            this.start();
        }
    }
    
    start() {
        try {
            this.recognition.start();
        } catch (e) {
            if (e.name === 'InvalidStateError') {
                this.status.textContent = '请稍候再试';
            }
        }
    }
    
    stop() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
        }
    }
}

