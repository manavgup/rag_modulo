import DOMPurify from 'dompurify';

/**
 * Sanitizes HTML content to prevent XSS attacks
 *
 * @param dirty - The untrusted HTML string to sanitize
 * @returns Sanitized HTML safe for rendering
 *
 * Usage:
 * ```tsx
 * <div dangerouslySetInnerHTML={{ __html: sanitizeHtml(untrustedContent) }} />
 * ```
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'code', 'pre'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
    ALLOW_DATA_ATTR: false,
  });
}

/**
 * Sanitizes text content - React escapes by default, but this provides explicit sanitization
 *
 * @param text - The untrusted text to sanitize
 * @returns Sanitized text safe for rendering
 */
export function sanitizeText(text: string): string {
  // React escapes text content by default, but we can add extra protection
  // Remove any potential script tags or dangerous patterns
  return text
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+\s*=/gi, ''); // Remove event handlers like onclick=
}
