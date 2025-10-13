import React from 'react';

export type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info';
export type BadgeSize = 'sm' | 'md' | 'lg';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
}

const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  className = '',
}) => {
  // Variant classes
  const variantClasses = {
    default: 'bg-gray-20 text-gray-100',
    success: 'bg-green-10 text-green-60',
    warning: 'bg-yellow-10 text-yellow-50',
    error: 'bg-red-10 text-red-50',
    info: 'bg-blue-10 text-blue-60',
  };

  // Size classes
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  const combinedClasses = `inline-flex items-center font-medium rounded-full ${variantClasses[variant]} ${sizeClasses[size]} ${className}`;

  return <span className={combinedClasses}>{children}</span>;
};

export default Badge;
