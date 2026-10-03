import { useState } from 'react';
import { ERROR_MESSAGE, generateBrief, safeSourceUrl } from './api.js';
import demo from './demo-brief.json';

function Preference({ preference }) {
  return <aside className="preferences" aria-labelledby="preference-title">
    <div className="section-label">UNDERSTOOD, NOT ASSUMED</div>
    <h2 id="preference-title">Your Preference</h2>
    <dl>{[['Locations', 'locations'], ['Categories', 'categories'], ['Keywords', 'keywords'], ['Exclude', 'exclude_keywords']].map(([label, key]) =>
      <div key={key}><dt>{label}</dt><dd>{preference[key].length ? preference[key].join(' / ') : '未指定'}</dd></div>
    )}</dl>
  </aside>;
}

function RecommendationCard({ item, index }) {
  const url = safeSourceUrl(item.source_url || item.link);
  return <article className="recommendation" aria-label={item.title}>
    <div className="card-top"><span className="category">{item.category}</span><span className="rank">#{String(item.final_rank || index + 1).padStart(2, '0')}</span></div>
    <h3>{item.title}</h3>
    <p className="organization">{item.organization || item.company}</p>
    <p className="location"><span aria-hidden="true">⌖</span> {item.location}</p>
    <div className="scores">
      <div><span>Match Score</span><strong>{item.match_score}<small>/100</small></strong></div>
      <div><span>Priority Score</span><strong>{item.priority_score}<small>/100</small></strong></div>
    </div>
    <div className="why"><h4>Why Recommended</h4><ul>{item.why_recommended.map((reason, i) => <li key={i}>{reason}</li>)}</ul></div>
    <div className="card-footer"><div><span>Deadline</span><strong>{item.deadline || '未注明'}{item.deadline_expired ? ' · 已截止' : ''}</strong></div>
      {url && <a href={url} target="_blank" rel="noopener noreferrer">View Source <span aria-hidden="true">↗</span></a>}
    </div>
    <p className="source">Source · {item.source}</p>
  </article>;
}

export default function App() {
  const [text, setText] = useState('');
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [offline, setOffline] = useState(false);
  const [submitted, setSubmitted] = useState('');

  async function submit(event) {
    event.preventDefault();
    if (!text.trim()) { setError('请先输入你的需求。'); return; }
    setLoading(true); setError(''); setBrief(null); setOffline(false);
    try {
      const result = await generateBrief(text.trim());
      setBrief(result); setSubmitted(text.trim());
    } catch { setError(ERROR_MESSAGE); }
    finally { setLoading(false); }
  }

  function loadDemo() {
    setText(demo.request); setSubmitted(demo.request); setBrief(demo.brief);
    setOffline(true); setError('');
  }

  const mock = brief?.recommended_items.some((item) => /mock/i.test(item.source));
  const highMatches = brief?.recommended_items.filter((item) => item.match_score >= 80 && item.match_score <= 100).length || 0;

  return <>
    <header className="site-header"><div className="header-inner">
      <a className="brand" href="#"><span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>BriefFlow</a>
      <span className="edition">PERSONAL INTELLIGENCE <span>V0.1</span></span>
    </div></header>
    <main>
      <section className="intro"><div className="eyebrow"><span /> YOUR NEXT OPPORTUNITY, IN FOCUS</div>
        <h1>一句话，创建属于你的<br className="desktop-break" /> <em>AI 情报站</em></h1>
        <p>说出你在寻找什么。让信息更有方向，让机会清晰可见。</p>
      </section>
      <section className="composer" aria-labelledby="input-title">
        <div className="composer-heading"><h2 id="input-title">你想发现什么？</h2><span>01 / DEFINE YOUR BRIEF</span></div>
        <form onSubmit={submit}>
          <label className="sr-only" htmlFor="request">你的需求</label>
          <textarea id="request" value={text} onChange={(event) => setText(event.target.value)} maxLength={2000} disabled={loading}
            placeholder="我是金融专业大三学生，帮我找粤港澳金融实习，不要销售岗。" aria-describedby="input-hint" />
          <div className="composer-bottom"><p id="input-hint">加入地点、方向和排除条件，让推荐更贴近你。</p>
            <button className="primary" type="submit" disabled={loading}>{loading ? 'Loading...' : 'Generate Brief'} <span aria-hidden="true">→</span></button>
          </div>
        </form>
        <div className="examples"><span>快速开始</span><button disabled={loading} onClick={() => setText(demo.request)}>粤港澳金融实习</button>
          <button disabled={loading} onClick={() => setText('想找深圳的科研机会，不要销售岗。')}>深圳科研机会</button>
          <button className="demo-button" disabled={loading} onClick={loadDemo}>加载离线示例</button>
        </div>
      </section>
      {loading && <p className="loading" role="status">Loading... 正在整理你的 Brief。</p>}
      {error && <div className="error" role="alert"><strong>{error}</strong><p>你可以重试，或选择“加载离线示例”查看固定演示内容。</p></div>}
      {brief ? <section className="results" aria-label="Brief results" aria-live="polite">
        <div className="results-top"><div><div className="section-label">02 / YOUR PERSONALIZED BRIEF</div><h2>为你整理的机会</h2></div>
          <span className={`mode ${offline || mock ? 'mock' : ''}`}>{offline ? 'Demo / Mock Mode · 离线示例' : mock ? 'Demo / Mock Mode · API' : 'API result'}</span>
        </div>
        {(offline || mock) && <p className="mode-note">{offline ? `固定 Mock 示例（${demo.generated_on}），未调用后端，不是对新需求的实时推荐。` : '后端返回的是 Mock 数据，用于演示，不代表真实招聘或活动信息。'}</p>}
        <p className="submitted">本次需求：{submitted}</p>
        <div className="brief-overview"><Preference preference={brief.preference} />
          <div className="summary"><div className="section-label">AT A GLANCE</div><h2>Your Brief</h2>
            <div className="summary-counts"><div><strong>{brief.total_items}</strong><span>recommended items</span></div><div><strong>{highMatches}</strong><span>high matches · ≥80</span></div></div>
            <p>{brief.summary}</p>
          </div>
        </div>
        {brief.total_items === 0 ? <div className="empty"><h3>暂时没有匹配的信息</h3><p>试试更宽的地点或类别，或补充具体关键词。</p></div> :
          <div className="cards">{brief.recommended_items.map((item, index) => <RecommendationCard key={`${item.job_id || item.item_id}-${index}`} item={item} index={index} />)}</div>}
      </section> : !loading && !error && <section className="welcome" aria-label="How it works"><div><span>01</span><h3>描述需求</h3><p>用自然语言表达目标与偏好</p></div><div><span>02</span><h3>发现匹配</h3><p>按匹配程度与时效整理信息</p></div><div><span>03</span><h3>了解原因</h3><p>查看评分、推荐理由与原始来源</p></div></section>}
      <footer>BriefFlow <span>少一点信息噪音，多一点明确方向。</span><span>V0.1 · Web MVP</span></footer>
    </main>
  </>;
}
