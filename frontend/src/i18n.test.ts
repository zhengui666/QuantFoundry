import { beforeEach, describe, expect, it } from 'vitest';
import i18n, {
  applyServerSettingsLocale,
  getRestoredServerLocale,
  resetServerSettingsLocale,
} from './i18n';

describe('server Settings locale projection', () => {
  beforeEach(() => {
    localStorage.clear();
    resetServerSettingsLocale();
  });

  it('applies server-decoded language/timezone display settings in memory', async () => {
    await applyServerSettingsLocale({ language: 'en', timezone: 'America/New_York' });
    expect(i18n.language).toBe('en');
    expect(document.documentElement.lang).toBe('en');
    expect(document.documentElement.dataset.timezone).toBe('America/New_York');
    expect(getRestoredServerLocale()).toEqual({ language: 'en', timezone: 'America/New_York' });
  });

  it('ignores browser locale data because it is not configuration truth', () => {
    localStorage.setItem('qf.server-settings.locale', '{broken');
    expect(getRestoredServerLocale()).toBeUndefined();
  });

  it('fails closed to UTC for invalid newly applied server timezones', async () => {
    await applyServerSettingsLocale({ language: 'zh-CN', timezone: 'Also/Invalid' });
    expect(getRestoredServerLocale()).toEqual({ language: 'zh-CN', timezone: 'UTC' });
    expect(document.documentElement.dataset.timezone).toBe('UTC');
  });
});
