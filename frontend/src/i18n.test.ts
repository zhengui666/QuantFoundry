import { beforeEach, describe, expect, it } from 'vitest';
import i18n, { applyServerSettingsLocale, getRestoredServerLocale } from './i18n';

describe('server Settings locale projection', () => {
  beforeEach(() => localStorage.clear());

  it('applies and persists only server-decoded language/timezone display settings', async () => {
    await applyServerSettingsLocale({ language: 'en', timezone: 'America/New_York' });
    expect(i18n.language).toBe('en');
    expect(document.documentElement.lang).toBe('en');
    expect(document.documentElement.dataset.timezone).toBe('America/New_York');
    expect(getRestoredServerLocale()).toEqual({
      language: 'en',
      timezone: 'America/New_York',
    });
  });

  it('ignores malformed browser locale data instead of guessing server Settings', () => {
    localStorage.setItem('qf.server-settings.locale', '{broken');
    expect(getRestoredServerLocale()).toBeUndefined();
  });

  it('fails closed to UTC for invalid persisted or newly applied server timezones', async () => {
    localStorage.setItem(
      'qf.server-settings.locale',
      JSON.stringify({ language: 'en', timezone: 'Invalid/Zone' }),
    );
    expect(getRestoredServerLocale()).toEqual({ language: 'en', timezone: 'UTC' });
    await applyServerSettingsLocale({ language: 'zh-CN', timezone: 'Also/Invalid' });
    expect(getRestoredServerLocale()).toEqual({ language: 'zh-CN', timezone: 'UTC' });
    expect(document.documentElement.dataset.timezone).toBe('UTC');
  });
});
