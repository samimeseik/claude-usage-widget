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

function timeUntilReset(resetIso) {
  if (!resetIso) return '';
  var diff = Math.max(0, new Date(resetIso) - new Date());
  var h = Math.floor(diff / 3600000);
  var m = Math.floor((diff % 3600000) / 60000);
  if (h > 24) return Math.floor(h / 24) + 'd ' + (h % 24) + 'h';
  if (h > 0) return h + 'h ' + m + 'm';
  return m + 'm';
}

function barColor(pct) {
  if (pct >= 80) return '#ff453a';
  if (pct >= 60) return '#ff9f0a';
  return null;
}

function barGrad(pct, def) {
  return barColor(pct) || def;
}

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
    borderRadius: 12, padding: '10px 12px 8px 12px', marginBottom: 6,
  },
  lbl: {
    fontSize: 9, fontWeight: 600, color: 'rgba(255,255,255,0.4)',
    textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 4,
  },
  row: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 6 },
  rst: { fontSize: 9, color: 'rgba(255,255,255,0.28)' },
  bg: { height: 4, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.07)', overflow: 'hidden' },
};

function formatTs(ts) {
  if (!ts) return '';
  try {
    var d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  } catch(e) { return ''; }
}

export const render = function(props) {
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

  var fh = data && data.five_hour || {};
  var sd = data && data.seven_day || {};
  var sn = data && data.seven_day_sonnet || null;

  var sp = Math.round(fh.utilization || 0);
  var wp = Math.round(sd.utilization || 0);
  var snp = sn ? Math.round(sn.utilization || 0) : 0;
  var trends = data && data._trends || {};
  var tArrow = { up: ' ↑', down: ' ↓', stable: '' };

  var dotColor = errorMsg ? '#ff453a' : isStale ? '#ff9f0a' : '#30d158';
  var dotShadow = errorMsg ? '0 0 6px rgba(255,69,58,0.5)' : isStale ? '0 0 6px rgba(255,159,10,0.5)' : '0 0 6px rgba(48,209,88,0.5)';
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
          <div style={s.title}>Claude Usage</div>
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
          <div style={s.card}>
            <div style={s.lbl}>Current Session</div>
            <div style={s.row}>
              <span style={pctStyle(barColor(sp) || '#0a84ff')}>{sp}%{tArrow[trends.five_hour] || ''}</span>
              <span style={s.rst}>resets in {timeUntilReset(fh.resets_at)}</span>
            </div>
            <div style={s.bg}>
              <div style={{height:'100%', borderRadius:2, width: Math.max(sp,1)+'%', background: barGrad(sp, 'linear-gradient(90deg, #0a84ff, #5e5ce6)')}} />
            </div>
          </div>

          <div style={s.card}>
            <div style={s.lbl}>Weekly — All Models</div>
            <div style={s.row}>
              <span style={pctStyle(barColor(wp) || '#bf5af2')}>{wp}%{tArrow[trends.seven_day] || ''}</span>
              <span style={s.rst}>resets in {timeUntilReset(sd.resets_at)}</span>
            </div>
            <div style={s.bg}>
              <div style={{height:'100%', borderRadius:2, width: Math.max(wp,1)+'%', background: barGrad(wp, 'linear-gradient(90deg, #bf5af2, #5e5ce6)')}} />
            </div>
          </div>

          {sn ? (
            <div style={s.card}>
              <div style={s.lbl}>Weekly — Sonnet</div>
              <div style={s.row}>
                <span style={pctStyle(barColor(snp) || '#30d158')}>{snp}%</span>
                <span style={s.rst}>resets in {timeUntilReset(sn.resets_at)}</span>
              </div>
              <div style={s.bg}>
                <div style={{height:'100%', borderRadius:2, width: Math.max(snp,1)+'%', background: barGrad(snp, 'linear-gradient(90deg, #30d158, #34c759)')}} />
              </div>
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
