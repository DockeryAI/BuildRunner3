/**
 * PRD Chat Interface - Conversational interface for PRD updates
 *
 * Features:
 * - Natural language command processing
 * - Conversation history
 * - Confirmation dialogs for changes
 * - Real-time validation
 * - Multi-turn conversations
 */

import React, { useState, useEffect, useRef } from 'react';
import { usePRDStore } from '../stores/prdStore';
import './PRDChatInterface.css';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  updates?: any;
  success?: boolean;
}

interface PRDChatInterfaceProps {
  onClose?: () => void;
}

export function PRDChatInterface({ onClose }: PRDChatInterfaceProps) {
  const {
    prd,
    isLoading,
    parseNaturalLanguage,
    updatePRD
  } = usePRDStore();

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "👋 Hi! I'm your PRD assistant. You can tell me what changes you'd like to make in plain English.\n\nTry:\n• \"Add a user authentication feature\"\n• \"Remove the payment feature\"\n• \"Change project name to MyApp\"\n• \"Update feature-1 priority to high\"",
      timestamp: new Date()
    }
  ]);

  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingUpdate, setPendingUpdate] = useState<any>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const addMessage = (role: Message['role'], content: string, updates?: any, success?: boolean) => {
    const message: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
      updates,
      success
    };
    setMessages(prev => [...prev, message]);
  };

  const handleSendMessage = async () => {
    const userInput = input.trim();
    if (!userInput || isProcessing) return;

    // Add user message
    addMessage('user', userInput);
    setInput('');
    setIsProcessing(true);

    try {
      // Parse natural language
      const result = await parseNaturalLanguage(userInput);

      if (!result.success) {
        addMessage('assistant', `❌ I couldn't understand that command. ${result.preview || 'Try rephrasing?'}`, null, false);
        setIsProcessing(false);
        return;
      }

      // Show what we understood and ask for confirmation
      const preview = formatUpdatePreview(result.updates);
      addMessage('assistant', `I understand you want to:\n\n${preview}\n\nIs this correct?`, result.updates);
      setPendingUpdate(result.updates);

    } catch (error) {
      addMessage('assistant', `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`, null, false);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleConfirmUpdate = async () => {
    if (!pendingUpdate) return;

    setIsProcessing(true);
    addMessage('system', '⏳ Applying changes...');

    try {
      await updatePRD(pendingUpdate);
      addMessage('assistant', '✅ Changes applied successfully! The PRD has been updated and the plan is regenerating.', null, true);
      setPendingUpdate(null);
    } catch (error) {
      addMessage('assistant', `❌ Failed to apply changes: ${error instanceof Error ? error.message : 'Unknown error'}`, null, false);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancelUpdate = () => {
    addMessage('assistant', 'No problem! What else would you like to change?');
    setPendingUpdate(null);
  };

  const formatUpdatePreview = (updates: any): string => {
    if (updates.add_feature) {
      return `➕ Add feature: "${updates.add_feature.name}" (Priority: ${updates.add_feature.priority})`;
    }
    if (updates.remove_feature) {
      const feature = prd?.features.find(f => f.id === updates.remove_feature);
      return `🗑️ Remove feature: "${feature?.name || updates.remove_feature}"`;
    }
    if (updates.update_feature) {
      const feature = prd?.features.find(f => f.id === updates.update_feature.id);
      const updateFields = Object.keys(updates.update_feature.updates).join(', ');
      return `✏️ Update feature "${feature?.name || updates.update_feature.id}": ${updateFields}`;
    }
    if (updates.project_name) {
      return `✏️ Change project name to: "${updates.project_name}"`;
    }
    if (updates.overview) {
      return `✏️ Update project overview`;
    }
    return JSON.stringify(updates, null, 2);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const suggestedCommands = [
    "Add a user dashboard feature",
    "Remove feature-1",
    "Change all priorities to high",
    "Update project name"
  ];

  return (
    <div className="prd-chat-interface">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-left">
          <h3>💬 PRD Chat Assistant</h3>
          {prd && <span className="project-name">{prd.project_name}</span>}
        </div>
        {onClose && (
          <button onClick={onClose} className="btn-close">✕</button>
        )}
      </div>

      {/* Messages Area */}
      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`chat-message message-${message.role}`}>
            <div className="message-avatar">
              {message.role === 'user' ? '👤' : message.role === 'assistant' ? '🤖' : 'ℹ️'}
            </div>
            <div className="message-content">
              <div className="message-text">{message.content}</div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}

        {/* Confirmation Buttons */}
        {pendingUpdate && !isProcessing && (
          <div className="confirmation-buttons">
            <button onClick={handleConfirmUpdate} className="btn-confirm">
              ✅ Yes, apply these changes
            </button>
            <button onClick={handleCancelUpdate} className="btn-cancel">
              ❌ No, cancel
            </button>
          </div>
        )}

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="processing-indicator">
            <span className="spinner">⚡</span> Processing...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="chat-input-area">
        {/* Suggested Commands */}
        {messages.length <= 1 && (
          <div className="suggested-commands">
            <span className="suggested-label">Try these:</span>
            {suggestedCommands.map((cmd, i) => (
              <button
                key={i}
                onClick={() => setInput(cmd)}
                className="suggested-command"
              >
                {cmd}
              </button>
            ))}
          </div>
        )}

        {/* Input Box */}
        <div className="chat-input-box">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your command... (e.g., 'add authentication feature')"
            disabled={isProcessing}
            className="chat-input"
          />
          <button
            onClick={handleSendMessage}
            disabled={!input.trim() || isProcessing}
            className="btn-send"
          >
            📤
          </button>
        </div>

        <div className="chat-help">
          <span>💡 Tip: Be specific about what you want to change. Press Enter to send.</span>
        </div>
      </div>
    </div>
  );
}

export default PRDChatInterface;
