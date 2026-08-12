import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import i18n from '../i18n';
import { DomainComponentGallery } from './components.stories';

afterEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

describe('formal P0 domain component matrix', () => {
  it('instantiates the formal domain components with English server-state copy', async () => {
    await i18n.changeLanguage('en');
    const { container } = render(<DomainComponentGallery state="default" />);
    expect(screen.getByText('AI interpretation')).toBeVisible();
    expect(screen.getByLabelText('Validation matrix')).toBeVisible();
    expect(screen.getByText('Holdout gate')).toBeVisible();
    expect(screen.getByText('Data capability matrix')).toBeVisible();
    expect(container.querySelectorAll('.domain-boundary').length).toBeGreaterThanOrEqual(17);
  });

  it('renders translated locked and disabled reasons from the same components', async () => {
    await i18n.changeLanguage('zh-CN');
    const { rerender } = render(<DomainComponentGallery state="locked" />);
    expect(screen.getAllByText(/已被服务端策略锁定/).length).toBeGreaterThanOrEqual(15);
    rerender(<DomainComponentGallery state="disabled" />);
    expect(screen.getAllByText('服务端能力声明已禁用此控件。').length).toBeGreaterThanOrEqual(15);
  });

  it('exposes deterministic keyboard focus and narrow states without replacing components', () => {
    const { container, rerender } = render(<DomainComponentGallery state="focus" />);
    expect(container.querySelectorAll('[data-domain-state="focus"]').length).toBeGreaterThanOrEqual(
      15,
    );
    rerender(<DomainComponentGallery state="narrow" />);
    expect(container.querySelector('.domain-story-narrow')).toBeInTheDocument();
    expect(
      container.querySelectorAll('[data-domain-state="narrow"]').length,
    ).toBeGreaterThanOrEqual(15);
  });
});
