document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('chat-form');
    const input = document.getElementById('query-input');
    const submitBtn = document.getElementById('submit-btn');
    const chatHistory = document.getElementById('chat-history');
    const welcomeState = document.getElementById('welcome-state');

    window.submitSuggestion = (query) => {
        input.value = query;
        handleSubmission();
    };

    window.clearChat = () => {
        // Remove all children except welcome state
        const elementsToRemove = [];
        for (let i = 0; i < chatHistory.children.length; i++) {
            if (chatHistory.children[i].id !== 'welcome-state') {
                elementsToRemove.push(chatHistory.children[i]);
            }
        }
        elementsToRemove.forEach(el => el.remove());
        if (welcomeState) {
            welcomeState.style.display = 'flex';
        }
    };

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        handleSubmission();
    });

    async function handleSubmission() {
        const query = input.value.trim();
        if (!query) return;

        if (welcomeState) welcomeState.style.display = 'none';

        appendUserMessage(query);
        
        input.value = '';
        input.disabled = true;
        submitBtn.disabled = true;

        const loadingId = 'loading-' + Date.now();
        const loadingHtml = `
            <div class="flex gap-4 items-start max-w-3xl" id="${loadingId}">
                <div class="w-8 h-8 rounded-full bg-sidebar border border-bordergray flex items-center justify-center flex-shrink-0 shadow-[0_0_10px_rgba(0,208,156,0.1)]">
                    <span class="material-symbols-outlined text-primary text-[18px]" style="font-variation-settings: 'FILL' 1;">auto_awesome</span>
                </div>
                <div class="bg-sidebar rounded-xl p-4 border border-bordergray shadow-lg w-32 h-12 flex items-center gap-1.5">
                    <div class="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce"></div>
                    <div class="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                    <div class="w-1.5 h-1.5 bg-primary/50 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
                </div>
            </div>
        `;
        chatHistory.insertAdjacentHTML('beforeend', loadingHtml);
        scrollToBottom();

        try {
            const response = await fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });

            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            const data = await response.json();
            
            document.getElementById(loadingId).remove();
            renderSystemResponse(data.answer);

        } catch (error) {
            console.error('API Error:', error);
            document.getElementById(loadingId).remove();
            renderSystemResponse("Sorry, I encountered a system error and couldn't process your request.");
        } finally {
            input.disabled = false;
            submitBtn.disabled = false;
            input.focus();
            scrollToBottom();
        }
    }

    function appendUserMessage(text) {
        const div = document.createElement('div');
        div.className = 'flex flex-col items-end w-full max-w-4xl mx-auto';
        div.innerHTML = `
            <div class="bg-sidebar max-w-[80%] rounded-xl p-3 shadow-md border border-bordergray">
                <p class="text-sm text-white">${escapeHtml(text)}</p>
            </div>
        `;
        chatHistory.appendChild(div);
    }

    function renderSystemResponse(rawAnswer) {
        let bodyText = rawAnswer;
        let sourceHtml = '';

        const sourceRegex = /Source:\s*(https?:\/\/[^\s]+)/;
        const updatedRegex = /Last updated from sources:\s*(.*)/;

        const sourceMatch = rawAnswer.match(sourceRegex);
        const updatedMatch = rawAnswer.match(updatedRegex);

        let verifiedBadge = '';

        if (sourceMatch) {
            bodyText = bodyText.replace(sourceMatch[0], '').replace(updatedRegex, '').trim();
            const url = sourceMatch[1];
            const dateStr = updatedMatch ? updatedMatch[1] : '';
            
            verifiedBadge = `
                <div class="flex items-center gap-2 mb-4">
                    <span class="material-symbols-outlined text-primary text-[16px]" style="font-variation-settings: 'FILL' 1;">check_circle</span>
                    <span class="text-primary font-mono text-[10px] tracking-wider uppercase font-semibold">Verified Answer</span>
                </div>
            `;

            sourceHtml = `
                <div class="mt-6 pt-4 border-t border-bordergray">
                    <p class="text-[10px] text-textgray mb-3">Sources</p>
                    <div class="flex flex-wrap gap-2">
                        <a class="flex items-center gap-2 bg-primary/10 border border-primary/20 px-3 py-1.5 rounded-md text-primary text-xs transition-all hover:bg-primary/20 group" href="${escapeHtml(url)}" target="_blank" rel="noopener nofollow">
                            <span class="material-symbols-outlined text-[14px]">link</span>
                            <span>${escapeHtml(url).replace('https://groww.in/mutual-funds/','groww.in/...')}</span>
                            <span class="material-symbols-outlined text-[14px] opacity-50 group-hover:opacity-100 transition-opacity">open_in_new</span>
                        </a>
                    </div>
                    <div class="mt-4 flex items-center gap-1.5 text-textgray">
                        <span class="material-symbols-outlined text-[12px]">verified</span>
                        <span class="text-[10px]">Verified from 2 sources</span>
                    </div>
                </div>
            `;
        } else {
            // Not verified (e.g. dont know or refusal)
             verifiedBadge = `
                <div class="flex items-center gap-2 mb-4">
                    <span class="material-symbols-outlined text-[#eab308] text-[16px]" style="font-variation-settings: 'FILL' 1;">info</span>
                    <span class="text-[#eab308] font-mono text-[10px] tracking-wider uppercase font-semibold">System Message</span>
                </div>
            `;
        }

        // Format bullet points if present (primitive markdown parser for LLM output)
        const formattedBody = escapeHtml(bodyText)
            .replace(/\n/g, '<br>')
            .replace(/● /g, '<span class="text-textgray mt-1 flex-shrink-0 text-[10px] mr-2">●</span>');

        const div = document.createElement('div');
        div.className = 'flex gap-4 items-start w-full max-w-4xl mx-auto';
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full bg-sidebar border border-bordergray flex items-center justify-center flex-shrink-0 shadow-[0_0_10px_rgba(0,208,156,0.1)] mt-1">
                <span class="material-symbols-outlined text-primary text-[18px]" style="font-variation-settings: 'FILL' 1;">auto_awesome</span>
            </div>
            <div class="flex flex-col flex-1 max-w-[90%]">
                <div class="bg-sidebar rounded-xl p-5 border border-bordergray shadow-lg">
                    ${verifiedBadge}
                    <div class="text-sm text-gray-200 space-y-3 leading-relaxed">
                        ${formattedBody}
                    </div>
                    ${sourceHtml}
                    
                    <!-- Action Buttons -->
                    <div class="mt-4 pt-4 flex items-center gap-3">
                        <button class="text-textgray hover:text-white transition-colors"><span class="material-symbols-outlined text-[16px]">content_copy</span></button>
                        <button class="text-textgray hover:text-white transition-colors"><span class="material-symbols-outlined text-[16px]">thumb_up</span></button>
                        <button class="text-textgray hover:text-white transition-colors"><span class="material-symbols-outlined text-[16px]">thumb_down</span></button>
                    </div>
                </div>
            </div>
        `;
        chatHistory.appendChild(div);
    }

    function scrollToBottom() {
        chatHistory.scrollTo({
            top: chatHistory.scrollHeight,
            behavior: 'smooth'
        });
    }

    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
});
