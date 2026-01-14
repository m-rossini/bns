import { logInfo, logWarn, logError } from './logger';

export function initializeOpenObserveRum(): void {
  try {
    // @ts-ignore - dynamic import, type may not be available
    const openobserveRum = window.OpenObserveRUM;
    // @ts-ignore - dynamic import, type may not be available
    const openobserveLogs = window.OpenObserveLogs;
    
    if (!openobserveRum || !openobserveLogs) {
      logWarn('OpenObserve RUM/Logs not loaded');
      return;
    }

    // @ts-ignore - Vite env type doesn't support dynamic access
    const token = import.meta.env.VITE_OPENOBSERVE_TOKEN || '';
    // @ts-ignore - Vite env type doesn't support dynamic access
    const site = import.meta.env.VITE_OPENOBSERVE_SITE || 'localhost:5080';
    // @ts-ignore - Vite env type doesn't support dynamic access
    const org = import.meta.env.VITE_OPENOBSERVE_ORG || 'default';
    // @ts-ignore - Vite env type doesn't support dynamic access
    const appId = import.meta.env.VITE_OPENOBSERVE_APP_ID || 'bns-app';

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
