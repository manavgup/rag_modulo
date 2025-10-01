import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import LightweightHeader from './LightweightHeader';
import LightweightSidebar from './LightweightSidebar';

interface LightweightLayoutProps {
  children: React.ReactNode;
}

const LightweightLayout: React.FC<LightweightLayoutProps> = ({ children }) => {
  const { user } = useAuth();
  const [isSideNavExpanded, setIsSideNavExpanded] = useState(false);

  const handleMenuClick = () => {
    setIsSideNavExpanded(!isSideNavExpanded);
  };

  // Mock user data for demonstration
  const mockUser = {
    id: user?.id || '1',
    username: user?.username || 'demo-user',
    email: user?.email || 'demo@example.com',
  };

  return (
    <div className="min-h-screen bg-gray-10">
      <LightweightHeader
        user={mockUser}
        onMenuClick={handleMenuClick}
        isSideNavExpanded={isSideNavExpanded}
      />

      <div className="flex">
        <LightweightSidebar
          isExpanded={isSideNavExpanded}
          onClose={() => setIsSideNavExpanded(false)}
        />

        <main className={`flex-1 transition-all duration-300 ${
          isSideNavExpanded ? 'lg:ml-64' : 'ml-0'
        }`}>
          <div className="min-h-screen">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default LightweightLayout;
