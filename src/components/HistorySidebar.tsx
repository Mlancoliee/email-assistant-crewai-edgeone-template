/**
 * HistorySidebar — leftmost column, lists past conversations.
 *
 * Pattern follows ChatGPT / Claude: clicking an item switches the active
 * conversation; the active one is highlighted; "新会话" up top kicks off a
 * fresh ``conversation_id``.
 *
 * Data:
 *   - feeds from ``/email/history`` action="list" (see ``../api.ts``).
 *   - title is derived backend-side from the first user message ("[task]
 *     仅分类邮件" / "处理待回邮件" / etc.) so this component doesn't need
 *     to inspect message contents.
 *
 * UX choices:
 *   - delete shows on row hover, never as a fixed icon — keeps the idle
 *     sidebar clean.
 *   - clicking the active row is a no-op (don't re-fetch / disturb state).
 *   - relative timestamps ("刚刚 / 5 分钟前 / 昨天 / 3 天前") so the user
 *     can scan recency without parsing absolute dates.
 */
import { useEffect, useState } from 'react';
import { tokens } from '../design-tokens';
import { Icon, IconSpinner } from '../icons';
import {
  ConversationListItem,
  deleteConversation,
  listConversations,
} from '../api';

interface Props {
  /** The currently active conversation_id — that row gets the highlight. */
  activeId: string;
  /** Click on a row in the sidebar. Caller switches to that conversation. */
  onSelect: (id: string) => void;
  /** Bumped externally to force a refresh (e.g. after a run finishes a new
   * conversation should appear). */
  refreshKey?: number;
  /** True while a run is in flight; we still allow switching but warn the
   * user (see the disabled style for non-active rows). */
  busy?: boolean;
}

export default function HistorySidebar({
  activeId,
  onSelect,
  refreshKey,
  busy,
}: Props) {
  const [items, setItems] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listConversations()
      .then((list) => {
        if (cancelled) return;
        setItems(list);
      })
      .catch((e) => {
        if (cancelled) return;
        setError((e as Error).message);
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    // Optimistic remove from list — feels snappier than waiting on the
    // round-trip. We pull from list immediately; on failure we re-fetch.
    setItems((prev) => prev.filter((x) => x.id !== id));
    try {
      await deleteConversation(id);
      // If the deleted one was active, caller should have moved on already
      // (we don't call onNewSession from here — that's an explicit user
      // action, not a side-effect of cleanup).
    } catch {
      // Rollback on error
      try {
        const fresh = await listConversations();
        setItems(fresh);
      } catch {
        /* ignore */
      }
    }
  }

  return (
    <aside style={shell}>
      <div style={topBar}>
        <h2 style={heading}>
          <Icon name="archive" size={13} />
          <span>历史会话</span>
        </h2>
      </div>

      {loading && (
        <div style={statusRow}>
          <IconSpinner size={11} />
          <span>加载中...</span>
        </div>
      )}
      {error && (
        <div style={{ ...statusRow, color: tokens.color.danger }}>
          <Icon name="alert-circle" size={11} />
          <span>{error}</span>
        </div>
      )}
      {!loading && !error && items.length === 0 && (
        <div style={emptyHint}>
          <div style={emptyTitle}>暂无历史</div>
          <div style={emptySub}>
            点击「仅分类」或「处理待回邮件」开始,完成后会自动归档到这里
          </div>
        </div>
      )}

      <ul style={list}>
        {items.map((item) => {
          const isActive = item.id === activeId;
          return (
            <li
              key={item.id}
              onClick={() => !isActive && onSelect(item.id)}
              style={{
                ...row,
                background: isActive ? tokens.color.brandSoft : 'transparent',
                borderColor: isActive ? tokens.color.brandBorder : 'transparent',
                cursor: isActive ? 'default' : busy ? 'wait' : 'pointer',
                opacity: !isActive && busy ? 0.6 : 1,
              }}
              title={isActive ? '当前会话' : '切换到这个会话'}
            >
              <div style={titleRow}>
                <span
                  style={{
                    ...titleText,
                    color: isActive ? tokens.color.brand : tokens.color.text,
                    fontWeight: isActive
                      ? tokens.fontWeight.semibold
                      : tokens.fontWeight.medium,
                  }}
                >
                  {trimmed(item.title)}
                </span>
                <button
                  type="button"
                  onClick={(e) => handleDelete(item.id, e)}
                  style={deleteBtn}
                  title="删除这个会话"
                  aria-label={`删除 ${item.title}`}
                >
                  <Icon name="trash-2" size={11} />
                </button>
              </div>
              <div style={metaRow}>
                <span>{relativeTime(item.lastMessageAt)}</span>
                <span style={metaDivider}>·</span>
                <span>{item.messageCount} 条</span>
              </div>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

// ─── helpers ────────────────────────────────────────────────────────────────

function trimmed(t: string): string {
  // The platform "[task] xxx" prefix in stored titles is good for
  // identification but visually heavy. Strip it for display.
  const stripped = t.replace(/^\s*\[task\]\s*/i, '').trim();
  return stripped.length > 36 ? stripped.slice(0, 36) + '…' : stripped || '(无标题)';
}

function relativeTime(ts: number): string {
  if (!ts) return '';
  const diff = Date.now() - ts;
  const minute = 60_000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (diff < minute) return '刚刚';
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`;
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`;
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`;
  // Older than a week: show abs date "5/22"
  const d = new Date(ts);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

// ─── styles ────────────────────────────────────────────────────────────────

const shell: React.CSSProperties = {
  flex: 1,
  minHeight: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: tokens.space[2],
  padding: tokens.space[3],
  background: tokens.color.surface,
  // No internal divider — the parent ChatLayout's overlay panel provides
  // the visual boundary (borderLeft + drop shadow).
  overflowY: 'auto',
  minWidth: 0,
};

const topBar: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: tokens.space[2],
  paddingBottom: tokens.space[2],
  borderBottom: `1px solid ${tokens.color.borderSubtle}`,
};

const heading: React.CSSProperties = {
  margin: 0,
  fontSize: tokens.fontSize.sm,
  fontWeight: tokens.fontWeight.semibold,
  color: tokens.color.textMuted,
  display: 'flex',
  alignItems: 'center',
  gap: tokens.space[2],
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
};

const list: React.CSSProperties = {
  listStyle: 'none',
  margin: 0,
  padding: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
};

const row: React.CSSProperties = {
  padding: `${tokens.space[2]}px ${tokens.space[2]}px`,
  borderRadius: tokens.radius.md,
  border: '1px solid transparent',
  transition: tokens.motion.fast,
  display: 'flex',
  flexDirection: 'column',
  gap: 2,
  position: 'relative',
};

const titleRow: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: tokens.space[1],
  minWidth: 0,
};

const titleText: React.CSSProperties = {
  flex: 1,
  fontSize: tokens.fontSize.base,
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  minWidth: 0,
};

const deleteBtn: React.CSSProperties = {
  // Visible only on row hover via the parent's :hover — but inline styles
  // don't support pseudo-classes, so we rely on opacity transition + always-
  // present-but-faint approach. (Hover styling uses CSS in index.css.)
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 22,
  height: 22,
  background: 'transparent',
  border: 'none',
  color: tokens.color.textSubtle,
  borderRadius: tokens.radius.sm,
  cursor: 'pointer',
  flexShrink: 0,
  // We dim the trash icon by default; index.css ``.history-row:hover``
  // brightens it. Without that CSS hook it's still visible enough to find.
  opacity: 0.5,
};

const metaRow: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 4,
  fontSize: tokens.fontSize.xs,
  color: tokens.color.textSubtle,
  fontFamily: tokens.font.mono,
};

const metaDivider: React.CSSProperties = {
  opacity: 0.5,
};

const statusRow: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: `${tokens.space[2]}px ${tokens.space[1]}px`,
  fontSize: tokens.fontSize.xs,
  color: tokens.color.textSubtle,
};

const emptyHint: React.CSSProperties = {
  padding: `${tokens.space[3]}px ${tokens.space[2]}px`,
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
};

const emptyTitle: React.CSSProperties = {
  fontSize: tokens.fontSize.sm,
  color: tokens.color.textMuted,
  fontWeight: tokens.fontWeight.medium,
};

const emptySub: React.CSSProperties = {
  fontSize: tokens.fontSize.xs,
  color: tokens.color.textSubtle,
  lineHeight: 1.5,
};
