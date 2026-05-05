import { css } from "uebersicht";

// Claude Code dashboard — companion widget showing only the Claude Code
// activity (today, projects, year heatmap, hourly, leaderboard).
// The main usage bars (session/weekly/sonnet) live in claude-usage.jsx.
//
// Position this widget on the OPPOSITE side of the screen from
// claude-usage.jsx (default: bottom-right). Both share the same
// fetch_usage.py backend so there's no extra API cost.

export const refreshFrequency = 120000;

export const command = "python3 $HOME/.claude-widget/fetch_usage.py 2>/dev/null || cat /tmp/claude_usage_cache.json 2>/dev/null || echo '{\"error\":\"Run install.sh first\"}'";

export const className = css`
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  width: 300px;
  pointer-events: none;
`;

function formatTokens(n) {
  if (!n) return '0';
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(0) + 'K';
  return String(n);
}

var s = {
  box: {
    borderRadius: 20, overflow: 'hidden',
    backdropFilter: 'blur(50px) saturate(190%)',
    WebkitBackdropFilter: 'blur(50px) saturate(190%)',
    backgroundColor: 'rgba(28, 28, 30, 0.78)',
    boxShadow: '0 10px 40px rgba(0,0,0,0.45), inset 0 0.5px 0 rgba(255,255,255,0.08)',
    border: '0.5px solid rgba(64,156,255,0.18)',
    padding: '16px 16px 14px 16px', color: '#fff',
  },
  hdr: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 },
  logo: {
    width: 32, height: 32, borderRadius: 8,
    background: 'linear-gradient(135deg, #64d2ff, #0a84ff)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 14, fontWeight: 700, color: '#fff', flexShrink: 0,
    boxShadow: '0 2px 8px rgba(10,132,255,0.3)',
  },
  title: { fontSize: 13, fontWeight: 600, color: '#fff', letterSpacing: '-0.3px' },
  sub: { fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 1 },
  todayCard: {
    backgroundColor: 'rgba(64,156,255,0.08)',
    borderRadius: 12, padding: '10px 12px', marginBottom: 8,
    border: '0.5px solid rgba(64,156,255,0.15)',
  },
  todayLbl: {
    fontSize: 9, fontWeight: 600, color: 'rgba(100,210,255,0.7)',
    textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6,
    display: 'flex', justifyContent: 'space-between',
  },
  todayBig: {
    fontSize: 22, fontWeight: 700, color: '#64d2ff',
    letterSpacing: '-0.8px', lineHeight: 1,
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
  ccMeta: {
    fontSize: 10, color: 'rgba(255,255,255,0.45)', marginTop: 4,
  },
  section: {
    marginTop: 4, marginBottom: 4,
    paddingTop: 8,
    borderTop: '0.5px solid rgba(255,255,255,0.08)',
  },
  sectionHdr: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
    marginBottom: 6,
  },
  sectionTitle: {
    fontSize: 9, fontWeight: 600,
    color: 'rgba(100,210,255,0.6)',
    textTransform: 'uppercase', letterSpacing: '0.6px',
  },
  sectionStats: {
    fontSize: 9, color: 'rgba(255,255,255,0.4)',
    fontVariantNumeric: 'tabular-nums',
  },
  // 7-day projects
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
  // Heatmap
  heatGrid: {
    display: 'grid',
    gridTemplateRows: 'repeat(7, 3px)',
    gridAutoFlow: 'column',
    gridAutoColumns: '3px',
    gap: 1,
    width: '100%',
  },
  // Hourly
  hourBars: {
    display: 'flex', alignItems: 'flex-end', gap: 1,
    height: 18,
  },
  hourLabels: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: 8, color: 'rgba(255,255,255,0.3)',
    marginTop: 2, fontVariantNumeric: 'tabular-nums',
  },
  // Leaderboard
  lbGroup: { marginTop: 6 },
  lbGroupHdr: {
    fontSize: 9, fontWeight: 600,
    color: 'rgba(255,255,255,0.45)',
    letterSpacing: '0.4px', marginBottom: 4,
  },
  lbRow: {
    display: 'grid',
    gridTemplateColumns: '1fr auto 50px auto',
    alignItems: 'center', gap: 8,
    fontSize: 10, marginBottom: 3,
  },
  lbName: {
    color: 'rgba(255,255,255,0.75)', fontWeight: 500,
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  lbCount: {
    color: 'rgba(255,255,255,0.45)', fontVariantNumeric: 'tabular-nums',
    fontSize: 9,
  },
  lbBarBg: {
    height: 4, borderRadius: 2,
    backgroundColor: 'rgba(255,255,255,0.06)',
    overflow: 'hidden',
  },
  lbShare: {
    fontSize: 9, color: 'rgba(255,255,255,0.4)',
    fontVariantNumeric: 'tabular-nums', minWidth: 28,
    textAlign: 'right',
  },
};

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

function Heatmap(props) {
  var buckets = props.buckets || [];
  var maxV = props.max || Math.max.apply(null, buckets.concat([1]));
  if (buckets.length === 0) return null;

  function colorFor(v) {
    if (v <= 0) return 'rgba(255,255,255,0.05)';
    var ratio = v / maxV;
    if (ratio < 0.2) return 'rgba(100,210,255,0.25)';
    if (ratio < 0.4) return 'rgba(100,210,255,0.45)';
    if (ratio < 0.6) return 'rgba(100,210,255,0.65)';
    if (ratio < 0.8) return 'rgba(100,210,255,0.85)';
    return '#64d2ff';
  }

  var cells = [];
  for (var i = 0; i < buckets.length; i++) {
    cells.push(
      <div key={i} style={{
        backgroundColor: colorFor(buckets[i]),
        borderRadius: 1,
      }} />
    );
  }
  return <div style={s.heatGrid}>{cells}</div>;
}

function HourlyBars(props) {
  var buckets = props.buckets || [];
  var maxV = props.max || Math.max.apply(null, buckets.concat([1]));
  var bars = [];
  for (var h = 0; h < 24; h++) {
    var v = buckets[h] || 0;
    var pct = maxV > 0 ? (v / maxV) : 0;
    var height = Math.max(1, Math.round(pct * 18));
    var opacity = v > 0 ? 0.85 : 0.15;
    bars.push(
      <div key={h} style={{
        flex: 1, backgroundColor: '#64d2ff', borderRadius: 1,
        height: height, opacity: opacity,
      }} />
    );
  }
  return <div style={s.hourBars}>{bars}</div>;
}

function LeaderboardGroup(props) {
  var items = props.items || [];
  var color = props.color || '#64d2ff';
  if (items.length === 0) return null;
  return (
    <div style={s.lbGroup}>
      <div style={s.lbGroupHdr}>{props.label}</div>
      {items.slice(0, 3).map(function (it, i) {
        var share = Math.max(0.5, it.share || 0);
        return (
          <div key={i} style={s.lbRow}>
            <span style={s.lbName}>{it.name}</span>
            <span style={s.lbCount}>{it.count}×</span>
            <div style={s.lbBarBg}>
              <div style={{
                height: '100%', borderRadius: 2,
                width: share + '%', backgroundColor: color,
              }} />
            </div>
            <span style={s.lbShare}>{(it.share || 0).toFixed(0)}%</span>
          </div>
        );
      })}
    </div>
  );
}

export const render = function (props) {
  var data = null, errorMsg = null;
  if (props.error || !props.output || !props.output.trim()) {
    errorMsg = 'No data';
  } else {
    try {
      data = JSON.parse(props.output);
      if (data.error && !data._code) errorMsg = data.error;
    } catch (e) { errorMsg = 'Parse error'; }
  }

  var cc = (data && data._code) || null;

  // If there's no Claude Code data, render nothing (don't show empty card)
  if (!cc || (!cc.sessions && !cc.messages)) {
    return <div />;
  }

  var now = new Date();
  var timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  return (
    <div style={s.box}>
      <div style={s.hdr}>
        <div style={s.logo}>⌘</div>
        <div style={{flex: 1}}>
          <div style={s.title}>Claude Code</div>
          <div style={s.sub}>{timeStr}</div>
        </div>
      </div>

      {/* Today */}
      <div style={s.todayCard}>
        <div style={s.todayLbl}>
          <span>Today</span>
          <span style={{color: 'rgba(255,255,255,0.3)'}}>
            {cc.sessions} {cc.sessions === 1 ? 'session' : 'sessions'}
          </span>
        </div>
        <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'space-between'}}>
          <span style={s.todayBig}>{formatTokens(cc.tokens_total)}</span>
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
      </div>

      {/* 7-day projects */}
      {cc.projects_7d && cc.projects_7d.length > 0 ? (
        <div style={s.section}>
          <div style={s.sectionHdr}>
            <span style={s.sectionTitle}>7-day breakdown</span>
          </div>
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

      {/* 1-year heatmap */}
      {cc.heatmap && cc.heatmap.active_days > 0 ? (
        <div style={s.section}>
          <div style={s.sectionHdr}>
            <span style={s.sectionTitle}>1-year activity</span>
            <span style={s.sectionStats}>
              {formatTokens(cc.heatmap.total)} · {cc.heatmap.active_days}d
            </span>
          </div>
          <Heatmap buckets={cc.heatmap.buckets} max={cc.heatmap.max} />
        </div>
      ) : null}

      {/* Hourly */}
      {cc.hourly && cc.hourly.total > 0 ? (
        <div style={s.section}>
          <div style={s.sectionHdr}>
            <span style={s.sectionTitle}>30-day hourly</span>
            <span style={s.sectionStats}>
              peak {String(cc.hourly.peak_hour).padStart(2, '0')}:00
            </span>
          </div>
          <HourlyBars buckets={cc.hourly.buckets} max={cc.hourly.max} />
          <div style={s.hourLabels}>
            <span>0</span><span>6</span><span>12</span><span>18</span><span>23</span>
          </div>
        </div>
      ) : null}

      {/* Leaderboard */}
      {cc.leaderboard && (
        cc.leaderboard.totals.agents > 0 ||
        cc.leaderboard.totals.skills > 0
      ) ? (
        <div style={s.section}>
          <div style={s.sectionHdr}>
            <span style={s.sectionTitle}>30-day leaderboard</span>
            <span style={s.sectionStats}>
              {cc.leaderboard.totals.agents}a · {cc.leaderboard.totals.skills}s
            </span>
          </div>
          {cc.leaderboard.agents && cc.leaderboard.agents.length > 0 ? (
            <LeaderboardGroup
              label="Agents" items={cc.leaderboard.agents} color="#bf5af2" />
          ) : null}
          {cc.leaderboard.skills && cc.leaderboard.skills.length > 0 ? (
            <LeaderboardGroup
              label="Skills" items={cc.leaderboard.skills} color="#30d158" />
          ) : null}
        </div>
      ) : null}
    </div>
  );
};
