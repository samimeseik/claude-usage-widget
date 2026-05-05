import { css } from "uebersicht";

export const refreshFrequency = 120000;

export const command = "python3 $HOME/.claude-widget/fetch_usage.py 2>/dev/null || cat /tmp/claude_usage_cache.json 2>/dev/null || echo '{\"error\":\"Run install.sh first\"}'";

export const className = css`
  position: fixed;
  bottom: 24px;
  left: 24px;
  z-index: 1;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  width: 280px;
  pointer-events: none;
`;

// ─── Time helpers ─────────────────────────────────────────────────

function formatReset(iso) {
  // Absolute, timezone-aware: "8:42 PM" / "Thu 8 PM" / "in 12m"
  if (!iso) return '';
  try {
    var d = new Date(iso);
    var now = new Date();
    var diffMs = d - now;
    var hours = diffMs / 3600000;
    if (hours < 0) return 'now';
    if (hours < 1) return 'in ' + Math.max(1, Math.floor(diffMs / 60000)) + 'm';
    var sameDay = d.getDate() === now.getDate() && d.getMonth() === now.getMonth();
    if (sameDay) {
      return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    }
    return d.toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' });
  } catch (e) { return ''; }
}

function formatEta(iso) {
  // "ETA 8:42 PM" or "ETA Thu 3 PM"
  if (!iso) return '';
  try {
    var d = new Date(iso);
    var now = new Date();
    var diffMs = d - now;
    if (diffMs <= 0) return '';
    var hours = diffMs / 3600000;
    if (hours < 1) return 'in ' + Math.max(1, Math.floor(diffMs / 60000)) + 'm';
    var sameDay = d.getDate() === now.getDate() && d.getMonth() === now.getMonth();
    if (sameDay) {
      return 'at ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    }
    return d.toLocaleString('en-US', { weekday: 'short', hour: 'numeric' });
  } catch (e) { return ''; }
}

function formatTs(ts) {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } catch (e) { return ''; }
}

function formatTokens(n) {
  if (!n) return '0';
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
  return String(n);
}

// ─── Color helpers ────────────────────────────────────────────────

function barColor(pct) {
  if (pct >= 80) return '#ff453a';
  if (pct >= 60) return '#ff9f0a';
  return null;
}
function barGrad(pct, def) { return barColor(pct) || def; }

// ─── Styles ──────────────────────────────────────────────────────

var s = {
  box: {
    borderRadius: 20, overflow: 'hidden',
    backdropFilter: 'blur(50px) saturate(190%)',
    WebkitBackdropFilter: 'blur(50px) saturate(190%)',
    backgroundColor: 'rgba(28, 28, 30, 0.78)',
    boxShadow: '0 10px 40px rgba(0,0,0,0.45), inset 0 0.5px 0 rgba(255,255,255,0.08)',
    border: '0.5px solid rgba(255,255,255,0.1)',
    padding: '16px 16px 12px 16px', color: '#fff',
  },
  hdr: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 },
  logo: {
    width: 32, height: 32, borderRadius: 8,
    background: 'linear-gradient(135deg, #d4a574, #c4956a)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 15, fontWeight: 700, color: '#fff', flexShrink: 0,
    boxShadow: '0 2px 8px rgba(180,120,70,0.3)',
  },
  title: { fontSize: 13, fontWeight: 600, color: '#fff', letterSpacing: '-0.3px' },
  sub: { fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 1 },
  card: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12, padding: '10px 12px 10px 12px', marginBottom: 6,
  },
  lbl: {
    fontSize: 9, fontWeight: 600, color: 'rgba(255,255,255,0.4)',
    textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 4,
  },
  row: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 6 },
  rst: { fontSize: 9, color: 'rgba(255,255,255,0.3)' },
  bg: { height: 4, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.07)', overflow: 'hidden' },
  metaRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginTop: 6, fontSize: 9,
  },
  eta: { color: 'rgba(255,255,255,0.45)', fontWeight: 500 },
  etaWarn: { color: '#ff9f0a', fontWeight: 600 },
  // Claude Code card
  ccCard: {
    backgroundColor: 'rgba(64,156,255,0.08)',
    borderRadius: 12,
    padding: '10px 12px 10px 12px',
    marginBottom: 6,
    border: '0.5px solid rgba(64,156,255,0.15)',
  },
  ccLbl: {
    fontSize: 9, fontWeight: 600, color: 'rgba(100,210,255,0.7)',
    textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6,
    display: 'flex', justifyContent: 'space-between',
  },
  ccBig: {
    fontSize: 22, fontWeight: 700, color: '#64d2ff',
    letterSpacing: '-0.8px', lineHeight: 1,
  },
  ccMeta: {
    fontSize: 10, color: 'rgba(255,255,255,0.45)', marginTop: 4,
  },
  ccChips: {
    display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap',
  },
  ccChip: {
    fontSize: 9, fontWeight: 500,
    backgroundColor: 'rgba(255,255,255,0.06)',
    color: 'rgba(255,255,255,0.65)',
    padding: '2px 6px', borderRadius: 4,
  },
  // Secondary account row
  acctCard: {
    backgroundColor: 'rgba(255,255,255,0.04)',
    borderRadius: 10,
    padding: '8px 12px',
    marginBottom: 6,
    border: '0.5px solid rgba(255,255,255,0.06)',
  },
  acctRow: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  acctLabel: {
    fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.7)',
    letterSpacing: '-0.1px',
  },
  acctMetric: {
    fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.85)',
    fontVariantNumeric: 'tabular-nums',
  },
  acctMetricMuted: {
    fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.3)',
    fontVariantNumeric: 'tabular-nums',
  },
  acctErr: {
    fontSize: 9, color: 'rgba(255,159,10,0.7)',
    marginLeft: 8,
  },
  // 7-day project drill-down
  projRow: {
    display: 'flex', alignItems: 'center', gap: 8,
    marginTop: 4, fontSize: 10,
  },
  projName: {
    flex: 1, color: 'rgba(255,255,255,0.7)', fontWeight: 500,
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  projTokens: {
    color: 'rgba(255,255,255,0.5)', fontVariantNumeric: 'tabular-nums',
    fontSize: 9,
  },
  projBars: {
    display: 'flex', alignItems: 'flex-end', gap: 1,
    height: 12, flexShrink: 0,
  },
  projBar: {
    width: 4, backgroundColor: '#64d2ff', borderRadius: 1,
    minHeight: 1,
  },
};

// ─── Sparkline ────────────────────────────────────────────────────

// 7-day project bar chart — 7 small vertical bars, height proportional to tokens
function ProjectBars(props) {
  var buckets = props.buckets || [];
  var maxVal = Math.max.apply(null, buckets.concat([1]));
  var bars = [];
  for (var i = 0; i < 7; i++) {
    var v = buckets[i] || 0;
    var pct = maxVal > 0 ? (v / maxVal) : 0;
    var height = Math.max(1, Math.round(pct * 12));
    var opacity = v > 0 ? 0.85 : 0.15;
    bars.push(
      <div key={i} style={{
        width: 4, height: height,
        backgroundColor: '#64d2ff', borderRadius: 1,
        opacity: opacity,
      }} />
    );
  }
  return <div style={s.projBars}>{bars}</div>;
}

function Sparkline(props) {
  var pts = props.points || [];
  if (pts.length < 2) return null;
  var w = 70, h = 12;
  var max = 100;
  var step = w / (pts.length - 1);
  var path = pts.map(function (p, i) {
    var x = i * step;
    var y = h - (Math.max(0, Math.min(p, max)) / max * h);
    return (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
  }).join(' ');
  return (
    <svg width={w} height={h} style={{display: 'block', flexShrink: 0}}>
      <path d={path} fill="none" stroke={props.color || 'rgba(255,255,255,0.5)'}
            strokeWidth="1.2" strokeOpacity="0.7"
            strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ─── Render ───────────────────────────────────────────────────────

export const render = function (props) {
  var data = null, errorMsg = null, isStale = false;

  if (props.error || !props.output || !props.output.trim()) {
    errorMsg = 'No data';
  } else {
    try {
      data = JSON.parse(props.output);
      if (data.error && !data.five_hour) errorMsg = data.error;
      if (data._stale) isStale = true;
    } catch (e) { errorMsg = 'Parse error'; }
  }

  var tsStr = data && data._ts ? formatTs(data._ts) : '';
  var now = new Date();
  var timeStr = tsStr || now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  var fh = (data && data.five_hour) || {};
  var sd = (data && data.seven_day) || {};
  var sn = (data && data.seven_day_sonnet) || null;
  var ex = (data && data.extra_usage) || null;
  var cc = (data && data._code) || null;
  var allAccounts = (data && data._accounts) || [];
  // Other accounts = everything except primary
  var primaryAcct = allAccounts.filter(function(a) { return a.primary; })[0];
  var otherAccounts = allAccounts.filter(function(a) { return !a.primary; });
  var primaryLabel = (primaryAcct && primaryAcct.label) || null;

  var sp = Math.round(fh.utilization || 0);
  var wp = Math.round(sd.utilization || 0);
  var snp = sn ? Math.round(sn.utilization || 0) : 0;

  var trends = (data && data._trends) || {};
  var eta = (data && data._eta) || {};
  var spark = (data && data._spark) || { s: [], w: [], sn: [] };
  var tArrow = { up: ' ↑', down: ' ↓', stable: '' };

  var dotColor = errorMsg ? '#ff453a' : isStale ? '#ff9f0a' : '#30d158';
  var dotShadow = errorMsg
    ? '0 0 6px rgba(255,69,58,0.5)'
    : isStale ? '0 0 6px rgba(255,159,10,0.5)' : '0 0 6px rgba(48,209,88,0.5)';
  var dotStyle = {
    width: 6, height: 6, borderRadius: 3, flexShrink: 0,
    backgroundColor: dotColor, boxShadow: dotShadow,
  };

  function pctStyle(c) {
    return { fontSize: 24, fontWeight: 700, color: c, letterSpacing: '-1px', lineHeight: 1 };
  }

  return (
    <div style={s.box}>
      <div style={s.hdr}>
        <div style={s.logo}>C</div>
        <div style={{flex: 1}}>
          <div style={s.title}>
            Claude Usage
            {primaryLabel && otherAccounts.length > 0 ? (
              <span style={{
                fontSize: 10, fontWeight: 500, color: 'rgba(255,255,255,0.4)',
                marginLeft: 6, letterSpacing: 0,
              }}>· {primaryLabel}</span>
            ) : null}
          </div>
          <div style={s.sub}>{isStale ? '⏳ cached · ' + timeStr : timeStr}</div>
        </div>
        <div style={dotStyle} />
      </div>

      {errorMsg ? (
        <div style={{
          backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 12,
          textAlign: 'center', color: 'rgba(255,255,255,0.35)',
          fontSize: 11, padding: '18px 12px',
        }}>{errorMsg}</div>
      ) : (
        <div>
          {/* Current Session */}
          <div style={s.card}>
            <div style={s.lbl}>Current Session</div>
            <div style={s.row}>
              <span style={pctStyle(barColor(sp) || '#0a84ff')}>{sp}%{tArrow[trends.five_hour] || ''}</span>
              <span style={s.rst}>resets {formatReset(fh.resets_at)}</span>
            </div>
            <div style={s.bg}>
              <div style={{height:'100%', borderRadius:2, width: Math.max(sp,1)+'%', background: barGrad(sp, 'linear-gradient(90deg, #0a84ff, #5e5ce6)')}} />
            </div>
            {(spark.s && spark.s.length > 1) || eta.five_hour ? (
              <div style={s.metaRow}>
                <Sparkline points={spark.s} color="#0a84ff" />
                {eta.five_hour ? (
                  <span style={s.etaWarn}>ETA {formatEta(eta.five_hour)}</span>
                ) : (
                  <span style={s.eta}>{spark.s && spark.s.length > 0 ? '12h trend' : ''}</span>
                )}
              </div>
            ) : null}
          </div>

          {/* Weekly — All Models */}
          <div style={s.card}>
            <div style={s.lbl}>Weekly — All Models</div>
            <div style={s.row}>
              <span style={pctStyle(barColor(wp) || '#bf5af2')}>{wp}%{tArrow[trends.seven_day] || ''}</span>
              <span style={s.rst}>resets {formatReset(sd.resets_at)}</span>
            </div>
            <div style={s.bg}>
              <div style={{height:'100%', borderRadius:2, width: Math.max(wp,1)+'%', background: barGrad(wp, 'linear-gradient(90deg, #bf5af2, #5e5ce6)')}} />
            </div>
            {(spark.w && spark.w.length > 1) || eta.seven_day ? (
              <div style={s.metaRow}>
                <Sparkline points={spark.w} color="#bf5af2" />
                {eta.seven_day ? (
                  <span style={s.etaWarn}>ETA {formatEta(eta.seven_day)}</span>
                ) : (
                  <span style={s.eta}>{spark.w && spark.w.length > 0 ? '12h trend' : ''}</span>
                )}
              </div>
            ) : null}
          </div>

          {/* Weekly — Sonnet */}
          {sn ? (
            <div style={s.card}>
              <div style={s.lbl}>Weekly — Sonnet</div>
              <div style={s.row}>
                <span style={pctStyle(barColor(snp) || '#30d158')}>{snp}%</span>
                <span style={s.rst}>resets {formatReset(sn.resets_at)}</span>
              </div>
              <div style={s.bg}>
                <div style={{height:'100%', borderRadius:2, width: Math.max(snp,1)+'%', background: barGrad(snp, 'linear-gradient(90deg, #30d158, #34c759)')}} />
              </div>
              {spark.sn && spark.sn.length > 1 ? (
                <div style={s.metaRow}>
                  <Sparkline points={spark.sn} color="#30d158" />
                  <span style={s.eta}>12h trend</span>
                </div>
              ) : null}
            </div>
          ) : null}

          {/* Extra Usage */}
          {ex && ex.is_enabled ? (
            <div style={s.card}>
              <div style={s.lbl}>Extra Usage</div>
              <div style={s.row}>
                <span style={{fontSize: 18, fontWeight: 700, color: '#64d2ff', letterSpacing: '-0.5px', lineHeight: 1}}>
                  ${(ex.used_credits || 0).toFixed(2)}
                </span>
                <span style={s.rst}>of ${ex.monthly_limit.toLocaleString()} {ex.currency || ''}</span>
              </div>
              <div style={s.bg}>
                <div style={{
                  height:'100%', borderRadius:2,
                  width: Math.max(((ex.used_credits||0)/Math.max(ex.monthly_limit,1))*100, 0.5)+'%',
                  background: 'linear-gradient(90deg, #64d2ff, #0a84ff)'
                }} />
              </div>
            </div>
          ) : null}

          {/* Other accounts (compact) */}
          {otherAccounts.length > 0 ? (
            <div style={s.acctCard}>
              <div style={{
                fontSize: 9, fontWeight: 600, color: 'rgba(255,255,255,0.4)',
                textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6,
              }}>Other Accounts</div>
              {otherAccounts.map(function(a, i) {
                var hasData = !!a.data;
                var asp = hasData ? Math.round((a.data.five_hour||{}).utilization || 0) : null;
                var awp = hasData ? Math.round((a.data.seven_day||{}).utilization || 0) : null;
                return (
                  <div key={i} style={Object.assign(
                    {}, s.acctRow,
                    i < otherAccounts.length - 1 ? {marginBottom: 4} : {}
                  )}>
                    <span style={s.acctLabel}>{a.label}</span>
                    {hasData ? (
                      <span>
                        <span style={s.acctMetric}>{asp}%</span>
                        <span style={s.acctMetricMuted}> · {awp}%</span>
                      </span>
                    ) : (
                      <span style={s.acctErr}>unavailable</span>
                    )}
                  </div>
                );
              })}
            </div>
          ) : null}

          {/* Claude Code (today) */}
          {cc && (cc.sessions > 0 || cc.messages > 0) ? (
            <div style={s.ccCard}>
              <div style={s.ccLbl}>
                <span>Claude Code · Today</span>
                <span style={{color: 'rgba(255,255,255,0.3)'}}>{cc.sessions} {cc.sessions === 1 ? 'session' : 'sessions'}</span>
              </div>
              <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'space-between'}}>
                <span style={s.ccBig}>{formatTokens(cc.tokens_total)}</span>
                <span style={{fontSize: 10, color: 'rgba(255,255,255,0.4)'}}>
                  tokens · {cc.messages} msg
                </span>
              </div>
              {cc.top_tools && cc.top_tools.length > 0 ? (
                <div style={s.ccChips}>
                  {cc.top_tools.slice(0, 4).map(function(t, i) {
                    return (
                      <span key={i} style={s.ccChip}>
                        {t.name} · {t.count}
                      </span>
                    );
                  })}
                </div>
              ) : null}
              {cc.top_projects && cc.top_projects.length > 0 ? (
                <div style={s.ccMeta}>
                  📁 {cc.top_projects[0].name}
                  {cc.top_projects.length > 1 ? ' · +' + (cc.top_projects.length - 1) + ' more' : ''}
                </div>
              ) : null}

              {cc.projects_7d && cc.projects_7d.length > 0 ? (
                <div style={{
                  marginTop: 10,
                  paddingTop: 8,
                  borderTop: '0.5px solid rgba(100,210,255,0.12)',
                }}>
                  <div style={{
                    fontSize: 9, fontWeight: 600,
                    color: 'rgba(100,210,255,0.6)',
                    textTransform: 'uppercase', letterSpacing: '0.6px',
                    marginBottom: 4,
                  }}>7-day breakdown</div>
                  {cc.projects_7d.slice(0, 4).map(function(p, i) {
                    return (
                      <div key={i} style={s.projRow}>
                        <span style={s.projName}>{p.name}</span>
                        <span style={s.projTokens}>{formatTokens(p.tokens)}</span>
                        <ProjectBars buckets={p.buckets} />
                      </div>
                    );
                  })}
                </div>
              ) : null}
            </div>
          ) : null}

          {data && data._update ? (
            <div style={{
              textAlign: 'center', fontSize: 9,
              color: '#ff9f0a', marginTop: 4,
            }}>v{data._update} available — run install.sh to update</div>
          ) : null}
        </div>
      )}
    </div>
  );
};
