/**
 * Notifications Component for BuildRunner 3.2
 *
 * Provides a notification system with toast messages, notification center,
 * and persistent notification storage.
 */

import React, { useState, useCallback, useContext, createContext, ReactNode } from 'react';
import './Notifications.css';

export enum NotificationType {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
}

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Date;
  duration?: number; // milliseconds, undefined = persistent
  action?: {
    label: string;
    onClick: () => void;
  };
  read: boolean;
}

interface NotificationContextType {
  notifications: Notification[];
  addNotification: (
    type: NotificationType,
    title: string,
    message: string,
    duration?: number,
    action?: Notification['action']
  ) => string;
  removeNotification: (id: string) => void;
  markAsRead: (id: string) => void;
  clearAll: () => void;
  unreadCount: number;
}

// Create notification context
const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

// NotificationProvider component
interface NotificationProviderProps {
  children: ReactNode;
}

export function NotificationProvider({ children }: NotificationProviderProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const addNotification = useCallback(
    (
      type: NotificationType,
      title: string,
      message: string,
      duration: number = 5000,
      action?: Notification['action']
    ): string => {
      const id = `notification-${Date.now()}-${Math.random()}`;

      const notification: Notification = {
        id,
        type,
        title,
        message,
        timestamp: new Date(),
        duration,
        action,
        read: false,
      };

      setNotifications((prev) => [notification, ...prev]);

      // Auto-remove notification after duration
      if (duration > 0) {
        setTimeout(() => {
          removeNotification(id);
        }, duration);
      }

      // Save to local storage
      saveNotificationsToStorage([notification, ...notifications]);

      return id;
    },
    [notifications]
  );

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
    localStorage.removeItem('buildrunner_notifications');
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const value: NotificationContextType = {
    notifications,
    addNotification,
    removeNotification,
    markAsRead,
    clearAll,
    unreadCount,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

// Hook to use notifications
export function useNotifications() {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider');
  }
  return context;
}

// Toast notification component
interface ToastProps {
  notification: Notification;
  onClose: (id: string) => void;
}

function Toast({ notification, onClose }: ToastProps) {
  const handleActionClick = () => {
    if (notification.action) {
      notification.action.onClick();
    }
    onClose(notification.id);
  };

  return (
    <div className={`toast toast-${notification.type}`}>
      <div className="toast-content">
        <div className="toast-icon">
          {notification.type === NotificationType.SUCCESS && '✓'}
          {notification.type === NotificationType.ERROR && '✕'}
          {notification.type === NotificationType.WARNING && '⚠'}
          {notification.type === NotificationType.INFO && 'ℹ'}
        </div>
        <div className="toast-text">
          <div className="toast-title">{notification.title}</div>
          {notification.message && (
            <div className="toast-message">{notification.message}</div>
          )}
        </div>
      </div>

      {notification.action && (
        <button className="toast-action" onClick={handleActionClick}>
          {notification.action.label}
        </button>
      )}

      <button
        className="toast-close"
        onClick={() => onClose(notification.id)}
        aria-label="Close notification"
      >
        ×
      </button>
    </div>
  );
}

// Toast container component
interface ToastContainerProps {
  notifications: Notification[];
  onClose: (id: string) => void;
}

function ToastContainer({ notifications, onClose }: ToastContainerProps) {
  const toastNotifications = notifications.filter((n) => n.duration !== undefined || n.duration === 0);

  return (
    <div className="toast-container">
      {toastNotifications.map((notification) => (
        <Toast
          key={notification.id}
          notification={notification}
          onClose={onClose}
        />
      ))}
    </div>
  );
}

// Notification center component
interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

function NotificationCenter({ isOpen, onClose }: NotificationCenterProps) {
  const {
    notifications,
    removeNotification,
    markAsRead,
    clearAll,
    unreadCount,
  } = useNotifications();

  const persistentNotifications = notifications.filter(
    (n) => n.duration === undefined || n.duration < 0
  );

  if (!isOpen) {
    return null;
  }

  return (
    <div className="notification-center-overlay" onClick={onClose}>
      <div className="notification-center" onClick={(e) => e.stopPropagation()}>
        <div className="notification-center-header">
          <h2>Notifications</h2>
          {unreadCount > 0 && (
            <span className="unread-badge">{unreadCount}</span>
          )}
          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="notification-center-content">
          {persistentNotifications.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🔔</div>
              <p>No notifications</p>
            </div>
          ) : (
            <div className="notifications-list">
              {persistentNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`notification-item ${
                    !notification.read ? 'unread' : ''
                  } notification-${notification.type}`}
                  onClick={() => markAsRead(notification.id)}
                >
                  <div className="notification-item-icon">
                    {notification.type === NotificationType.SUCCESS && '✓'}
                    {notification.type === NotificationType.ERROR && '✕'}
                    {notification.type === NotificationType.WARNING && '⚠'}
                    {notification.type === NotificationType.INFO && 'ℹ'}
                  </div>

                  <div className="notification-item-content">
                    <div className="notification-item-title">
                      {notification.title}
                    </div>
                    {notification.message && (
                      <div className="notification-item-message">
                        {notification.message}
                      </div>
                    )}
                    <div className="notification-item-time">
                      {formatTime(notification.timestamp)}
                    </div>
                  </div>

                  {notification.action && (
                    <button
                      className="notification-item-action"
                      onClick={(e) => {
                        e.stopPropagation();
                        notification.action?.onClick();
                        removeNotification(notification.id);
                      }}
                    >
                      {notification.action.label}
                    </button>
                  )}

                  <button
                    className="notification-item-close"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeNotification(notification.id);
                    }}
                    aria-label="Remove notification"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {persistentNotifications.length > 0 && (
          <div className="notification-center-footer">
            <button className="clear-all-button" onClick={clearAll}>
              Clear all
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Notification bell icon with badge
interface NotificationBellProps {
  onClick: () => void;
}

export function NotificationBell({ onClick }: NotificationBellProps) {
  const { unreadCount } = useNotifications();

  return (
    <button className="notification-bell" onClick={onClick} aria-label="Show notifications">
      <span className="bell-icon">🔔</span>
      {unreadCount > 0 && (
        <span className="notification-badge">{unreadCount}</span>
      )}
    </button>
  );
}

// Main Notifications component
export function Notifications() {
  const { notifications, removeNotification } = useNotifications();
  const [centerOpen, setCenterOpen] = useState(false);

  return (
    <>
      <ToastContainer
        notifications={notifications}
        onClose={removeNotification}
      />
      <NotificationBell onClick={() => setCenterOpen(true)} />
      <NotificationCenter
        isOpen={centerOpen}
        onClose={() => setCenterOpen(false)}
      />
    </>
  );
}

// Utility function to format time
function formatTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

// Helper hooks for quick notifications
export function useSuccessNotification() {
  const { addNotification } = useNotifications();
  return (title: string, message?: string) =>
    addNotification(NotificationType.SUCCESS, title, message || '', 5000);
}

export function useErrorNotification() {
  const { addNotification } = useNotifications();
  return (title: string, message?: string) =>
    addNotification(NotificationType.ERROR, title, message || '', 0); // persistent
}

export function useWarningNotification() {
  const { addNotification } = useNotifications();
  return (title: string, message?: string) =>
    addNotification(NotificationType.WARNING, title, message || '', 5000);
}

export function useInfoNotification() {
  const { addNotification } = useNotifications();
  return (title: string, message?: string) =>
    addNotification(NotificationType.INFO, title, message || '', 5000);
}

// Utility function to save notifications to local storage
function saveNotificationsToStorage(notifications: Notification[]) {
  try {
    const serialized = notifications.map((n) => ({
      ...n,
      timestamp: n.timestamp.toISOString(),
    }));
    localStorage.setItem(
      'buildrunner_notifications',
      JSON.stringify(serialized)
    );
  } catch (error) {
    console.error('Error saving notifications:', error);
  }
}
