import React, { createContext, useContext, useState } from 'react';
import { ToastNotification } from '@carbon/react';

const NotificationContext = createContext();

export const useNotification = () => {
  return useContext(NotificationContext);
};

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);

  const addNotification = (type, title, message) => {
    const id = Date.now();
    setNotifications((prevNotifications) => [
      ...prevNotifications,
      { id, type, title, message },
    ]);

    // Automatically remove the notification after 5 seconds
    setTimeout(() => {
      removeNotification(id);
    }, 5000);
  };

  const removeNotification = (id) => {
    setNotifications((prevNotifications) =>
      prevNotifications.filter((notification) => notification.id !== id)
    );
  };

  return (
    <NotificationContext.Provider value={{ addNotification, removeNotification }}>
      {children}
      <div className="notification-container">
        {notifications.map((notification) => (
          <ToastNotification
            key={notification.id}
            kind={notification.type}
            title={notification.title}
            subtitle={notification.message}
            caption={new Date().toLocaleTimeString()}
            onClose={() => removeNotification(notification.id)}
            lowContrast
          />
        ))}
      </div>
    </NotificationContext.Provider>
  );
};

export default NotificationContext;