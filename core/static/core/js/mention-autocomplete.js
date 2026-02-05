/**
 * MentionAutocomplete - User mention autocomplete system
 * Allows tagging users with @username in textareas
 */
class MentionAutocomplete {
    constructor(textarea) {
        this.textarea = textarea;
        this.dropdown = null;
        this.users = [];
        this.selectedIndex = -1;
        this.mentionStart = -1;
        this.currentQuery = '';
        this.debounceTimer = null;

        this.init();
    }

    init() {
        // Create dropdown element
        this.createDropdown();

        // Bind events
        this.textarea.addEventListener('input', this.handleInput.bind(this));
        this.textarea.addEventListener('keydown', this.handleKeydown.bind(this));
        this.textarea.addEventListener('blur', this.handleBlur.bind(this));

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.dropdown.contains(e.target) && e.target !== this.textarea) {
                this.hideDropdown();
            }
        });
    }

    createDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'mention-dropdown';
        this.dropdown.style.display = 'none';
        document.body.appendChild(this.dropdown);
    }

    handleInput(e) {
        const cursorPos = this.textarea.selectionStart;
        const textBeforeCursor = this.textarea.value.substring(0, cursorPos);

        // Check if @ was typed
        const lastAtIndex = textBeforeCursor.lastIndexOf('@');

        if (lastAtIndex !== -1) {
            // Check if @ is at start or preceded by whitespace
            const charBeforeAt = lastAtIndex > 0 ? textBeforeCursor[lastAtIndex - 1] : ' ';
            if (charBeforeAt === ' ' || charBeforeAt === '\n' || lastAtIndex === 0) {
                this.mentionStart = lastAtIndex;
                this.currentQuery = textBeforeCursor.substring(lastAtIndex + 1);

                // Only show if no space after @
                if (!this.currentQuery.includes(' ')) {
                    this.debouncedFetchUsers();
                } else {
                    this.hideDropdown();
                }
            } else {
                this.hideDropdown();
            }
        } else {
            this.hideDropdown();
        }
    }

    debouncedFetchUsers() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.fetchUsers(this.currentQuery);
        }, 300);
    }

    async fetchUsers(query) {
        try {
            const response = await fetch(`/api/users/search/?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.users = data.users;

            if (this.users.length > 0) {
                this.showDropdown();
            } else {
                this.hideDropdown();
            }
        } catch (error) {
            console.error('Error fetching users:', error);
            this.hideDropdown();
        }
    }

    showDropdown() {
        // Position dropdown
        const rect = this.textarea.getBoundingClientRect();
        let lineHeight = parseInt(window.getComputedStyle(this.textarea).lineHeight);
        if (isNaN(lineHeight)) lineHeight = 20; // Fallback if lineHeight is 'normal'

        this.dropdown.style.position = 'absolute';
        this.dropdown.style.left = rect.left + 'px';
        this.dropdown.style.top = (rect.top + window.scrollY + lineHeight + 5) + 'px';
        this.dropdown.style.minWidth = '250px';

        // Render users
        this.dropdown.innerHTML = this.users.map((user, index) => `
            <div class="mention-item ${index === this.selectedIndex ? 'selected' : ''}" data-index="${index}">
                <span class="mention-user-icon">👤</span>
                <div class="mention-user-info">
                    <div class="mention-username">@${user.username}</div>
                    <div class="mention-role">${user.role_display}</div>
                </div>
            </div>
        `).join('');

        // Add click handlers
        this.dropdown.querySelectorAll('.mention-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const index = parseInt(item.dataset.index);
                this.selectUser(index);
            });
        });

        this.dropdown.style.display = 'block';
        this.selectedIndex = 0;
    }

    hideDropdown() {
        this.dropdown.style.display = 'none';
        this.selectedIndex = -1;
        this.mentionStart = -1;
    }

    handleKeydown(e) {
        if (this.dropdown.style.display === 'none') return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, this.users.length - 1);
                this.updateSelection();
                break;

            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
                this.updateSelection();
                break;

            case 'Enter':
                if (this.selectedIndex >= 0) {
                    e.preventDefault();
                    this.selectUser(this.selectedIndex);
                }
                break;

            case 'Escape':
                e.preventDefault();
                this.hideDropdown();
                break;
        }
    }

    updateSelection() {
        const items = this.dropdown.querySelectorAll('.mention-item');
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    selectUser(index) {
        const user = this.users[index];
        if (!user) return;

        // Insert username
        const beforeMention = this.textarea.value.substring(0, this.mentionStart);
        const afterCursor = this.textarea.value.substring(this.textarea.selectionStart);

        this.textarea.value = beforeMention + '@' + user.username + ' ' + afterCursor;

        // Set cursor position after mention
        const newCursorPos = this.mentionStart + user.username.length + 2;
        this.textarea.setSelectionRange(newCursorPos, newCursorPos);

        // Trigger input event for any listeners
        this.textarea.dispatchEvent(new Event('input', { bubbles: true }));

        this.hideDropdown();
        this.textarea.focus();
    }

    handleBlur(e) {
        // Delay hiding to allow click on dropdown
        setTimeout(() => {
            if (!this.dropdown.contains(document.activeElement)) {
                this.hideDropdown();
            }
        }, 200);
    }

    destroy() {
        if (this.dropdown && this.dropdown.parentNode) {
            this.dropdown.parentNode.removeChild(this.dropdown);
        }
    }
}

// Auto-initialize on textareas with data-mention attribute
document.addEventListener('DOMContentLoaded', function () {
    const textareas = document.querySelectorAll('textarea[data-mention="true"]');
    textareas.forEach(textarea => {
        new MentionAutocomplete(textarea);
    });
});
