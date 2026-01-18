import { logInfo, logWarn, logError } from '@/observability/logger';

declare global {
  interface Window {
    OpenObserveRUM?: any;
    OpenObserveLogs?: any;
  }
}

export function initializeOpenObserveRum(): void {
  try {
    const openobserveRum = window.OpenObserveRUM;
    const openobserveLogs = window.OpenObserveLogs;
    
    if (!openobserveRum || !openobserveLogs) {
      logWarn('OpenObserve RUM/Logs not loaded');
      return;
    }

    const env = import.meta.env as Record<string, string | undefined>;
    const token = env.VITE_OPENOBSERVE_TOKEN || '';
    const site = env.VITE_OPENOBSERVE_SITE || 'localhost:5080';
    const org = env.VITE_OPENOBSERVE_ORG || 'default';
    const appId = env.VITE_OPENOBSERVE_APP_ID || 'bns-app';

    if (!token) {
      logWarn('OpenObserve RUM token not configured, skipping initialization');
      return;
    }

    // Initialize RUM
    openobserveRum.init({
      applicationId: appId,
      clientToken: token,
      site: site,
      organizationIdentifier: org,
      service: 'bns-simulation',
      env: import.meta.env.MODE || 'development',
      version: '0.1.0',
      trackResources: true,
      trackLongTasks: true,
      trackUserInteractions: true,
      apiVersion: 'v1',
      insecureHTTP: true,
      defaultPrivacyLevel: 'allow'
    });

    // Initialize Logs
    openobserveLogs.init({
      clientToken: token,
      site: site,
      organizationIdentifier: org,
      service: 'bns-simulation',
      env: import.meta.env.MODE || 'development',
      version: '0.1.0',
      forwardErrorsToLogs: true,
      insecureHTTP: true,
      apiVersion: 'v1'
    });

    // Set user context
    openobserveRum.setUser({
      id: 'session-user',
      name: 'BNS User',
      email: 'user@bns.local'
    });

    // Start session replay recording
    openobserveRum.startSessionReplayRecording();
    logInfo('OpenObserve RUM and Logs initialized with session replay');
  } catch (err) {
    logError('Failed to initialize OpenObserve RUM:', err);
  }
}
