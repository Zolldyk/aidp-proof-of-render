/**
 * Frontend configuration
 *
 * All environment variables are accessed through this config object.
 * Never use import.meta.env directly in business logic.
 */

export const config = {
  /**
   * Backend API base URL
   */
  API_BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',

  /**
   * Maximum file upload size in bytes (10MB default)
   */
  MAX_FILE_SIZE: Number(import.meta.env.VITE_MAX_FILE_SIZE) || 10485760,

  /**
   * Polling interval for render job status in milliseconds (3 seconds default)
   */
  POLLING_INTERVAL: Number(import.meta.env.VITE_POLLING_INTERVAL) || 3000,
} as const;
