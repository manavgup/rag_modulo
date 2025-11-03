import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Number of lines to show (for text skeletons)
   */
  lines?: number;
  /**
   * Width of the skeleton (e.g., 'full', '1/2', '200px')
   */
  width?: string;
  /**
   * Height of the skeleton (e.g., 'h-4', 'h-8', '32px')
   */
  height?: string;
  /**
   * Shape of the skeleton: 'text', 'circle', 'rect', or 'rounded'
   */
  variant?: 'text' | 'circle' | 'rect' | 'rounded';
  /**
   * Whether to show an animated shimmer effect
   */
  animated?: boolean;
}

/**
 * Skeleton loader component for showing loading states
 *
 * @example
 * // Text skeleton
 * <Skeleton lines={3} />
 *
 * // Circular avatar skeleton
 * <Skeleton variant="circle" width="48px" height="48px" />
 *
 * // Card skeleton
 * <Skeleton variant="rounded" width="full" height="200px" />
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  lines = 1,
  width = 'full',
  height = 'h-4',
  variant = 'text',
  animated = true,
  className = '',
  ...props
}) => {
  // Convert width to Tailwind class or inline style
  const widthClass = width === 'full' ? 'w-full' :
                     width.match(/^\d+\/\d+$/) ? `w-${width}` :
                     width.match(/^\d+px$/) ? '' : `w-${width}`;

  const widthStyle = width.match(/^\d+px$/) ? { width } : {};

  // Shape classes
  const shapeClasses = {
    text: 'rounded',
    circle: 'rounded-full',
    rect: '',
    rounded: 'rounded-lg',
  };

  const baseClasses = `bg-gray-30 ${shapeClasses[variant]} ${animated ? 'animate-pulse' : ''} ${widthClass} ${height} ${className}`.trim();

  if (variant === 'text' && lines > 1) {
    return (
      <div className="space-y-2" {...props}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            className={baseClasses}
            style={index === lines - 1 ? { ...widthStyle, width: '75%' } : widthStyle}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={baseClasses}
      style={widthStyle}
      {...props}
    />
  );
};

export default Skeleton;
