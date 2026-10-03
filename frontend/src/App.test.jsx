import React from 'react';
import { render, screen, within, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import App from './App.jsx';
import demo from './demo-brief.json';
import { ERROR_MESSAGE, generateBrief, safeSourceUrl } from './api.js';

function respond(brief = demo.brief) {
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => structuredClone(brief) });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

async function submit() {
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: '粤港澳金融实习' }));
  await user.click(screen.getByRole('button', { name: /Generate Brief/ }));
}

describe('Web MVP', () => {
  it('calls the API with the request text and renders returned cards', async () => {
    const fetch = respond(); render(<App />); await submit();
    expect(await screen.findAllByRole('article')).toHaveLength(9);
    expect(fetch).toHaveBeenCalledWith('/api/brief', expect.objectContaining({ method: 'POST', body: JSON.stringify({ user_text: demo.request }) }));
    expect(screen.getByText('Your Preference')).toBeInTheDocument();
    expect(screen.getByText('广州 / 深圳 / 香港 / 澳门')).toBeInTheDocument();
    expect(screen.getByText('Demo / Mock Mode · API')).toBeInTheDocument();
  });

  it('displays scores, reasons, dates, source and summary counts', async () => {
    respond(); render(<App />); await submit();
    const cards = await screen.findAllByRole('article');
    const first = within(cards[0]);
    expect(first.getByText('Match Score')).toBeInTheDocument();
    expect(first.getByText('Priority Score')).toBeInTheDocument();
    expect(first.getByText('100')).toBeInTheDocument();
    expect(first.getByText('Why Recommended')).toBeInTheDocument();
    expect(first.getByText(demo.brief.recommended_items[0].deadline)).toBeInTheDocument();
    expect(first.getByText('Source · BriefFlow Mock')).toBeInTheDocument();
    expect(first.getByRole('link', { name: /View Source/ })).toHaveAttribute('rel', 'noopener noreferrer');
    expect(screen.getByText('recommended items').previousElementSibling).toHaveTextContent('9');
    expect(screen.getByText('high matches · ≥80').previousElementSibling).toHaveTextContent('9');
  });

  it('shows loading and prevents duplicate submissions', async () => {
    let resolve;
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise((done) => { resolve = done; })));
    render(<App />); await submit();
    expect(screen.getByRole('status')).toHaveTextContent('Loading...');
    expect(screen.getByRole('button', { name: /Loading/ })).toBeDisabled();
    resolve({ ok: true, json: async () => demo.brief });
    await screen.findAllByRole('article');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows an empty state without cards', async () => {
    respond({ ...demo.brief, total_items: 0, recommended_items: [], summary: '没有匹配信息' });
    render(<App />); await submit();
    expect(await screen.findByText('暂时没有匹配的信息')).toBeInTheDocument();
    expect(screen.queryAllByRole('article')).toHaveLength(0);
  });

  it('shows a clear server error instead of silently substituting demo data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    render(<App />); await submit();
    expect(await screen.findByRole('alert')).toHaveTextContent(ERROR_MESSAGE);
    expect(screen.queryAllByRole('article')).toHaveLength(0);
  });

  it('offers an explicit local demo after connection failure', async () => {
    const fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    vi.stubGlobal('fetch', fetch); render(<App />); await submit();
    await screen.findByRole('alert');
    await userEvent.click(screen.getByRole('button', { name: '加载离线示例' }));
    expect(screen.getAllByRole('article')).toHaveLength(9);
    expect(screen.getByText('Demo / Mock Mode · 离线示例')).toBeInTheDocument();
    expect(screen.getByText(/固定 Mock 示例/)).toHaveTextContent('不是对新需求的实时推荐');
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('local demo works without any API call', async () => {
    const fetch = respond(); render(<App />);
    await userEvent.click(screen.getByRole('button', { name: '加载离线示例' }));
    expect(screen.getAllByRole('article')).toHaveLength(9);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('blank requests show validation and do not call API', async () => {
    const fetch = respond(); render(<App />);
    await userEvent.click(screen.getByRole('button', { name: /Generate Brief/ }));
    expect(screen.getByRole('alert')).toHaveTextContent('请先输入你的需求');
    expect(fetch).not.toHaveBeenCalled();
  });

  it('malformed API data shows error without crashing rendering', async () => {
    respond({ ...demo.brief, recommended_items: [null], total_items: 1 }); render(<App />); await submit();
    expect(await screen.findByRole('alert')).toHaveTextContent(ERROR_MESSAGE);
  });

  it('unsafe source URLs never become clickable', async () => {
    const brief = structuredClone(demo.brief);
    brief.recommended_items[0].source_url = 'javascript:alert(1)';
    respond(brief); render(<App />); await submit();
    const cards = await screen.findAllByRole('article');
    expect(within(cards[0]).queryByRole('link')).not.toBeInTheDocument();
    expect(safeSourceUrl('https://example.com')).toBe('https://example.com/');
  });

  it('a successful retry replaces the error', async () => {
    const fetch = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ ok: true, json: async () => demo.brief });
    vi.stubGlobal('fetch', fetch); render(<App />); await submit();
    await screen.findByRole('alert');
    await userEvent.click(screen.getByRole('button', { name: /Generate Brief/ }));
    await screen.findAllByRole('article');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('labels non-mock API results without a mock banner', async () => {
    const brief = structuredClone(demo.brief);
    brief.recommended_items.forEach((item) => { item.source = 'Public source'; });
    respond(brief); render(<App />); await submit();
    expect(await screen.findByText('API result')).toBeInTheDocument();
    expect(screen.queryByText(/Demo \/ Mock Mode/)).not.toBeInTheDocument();
  });

  it('aborts requests after the timeout', async () => {
    vi.useFakeTimers();
    try {
      vi.stubGlobal('fetch', vi.fn((_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted'))))));
      const pending = expect(generateBrief('test')).rejects.toThrow('aborted');
      await vi.advanceTimersByTimeAsync(20000);
      await pending;
    } finally { vi.useRealTimers(); }
  });
});
