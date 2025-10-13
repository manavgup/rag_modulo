import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  onClick?: () => void;
  hoverable?: boolean;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ children, className = '', padding = 'md', onClick, hoverable = false }, ref) => {
    // Base classes
    const baseClasses = 'bg-white border border-gray-20 rounded-lg shadow-sm';

    // Padding classes
    const paddingClasses = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    };

    // Hover classes
    const hoverClasses = hoverable || onClick ? 'hover:shadow-md cursor-pointer' : '';

    // Interactive classes
    const interactiveClasses = onClick ? 'transition-shadow duration-200' : '';

    const combinedClasses = `${baseClasses} ${paddingClasses[padding]} ${hoverClasses} ${interactiveClasses} ${className}`;

    return (
      <div ref={ref} className={combinedClasses} onClick={onClick}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export default Card;
