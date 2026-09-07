import React from 'react'

// Matches URLs (http/https or bare t.co-style domains), @mentions and #hashtags.
// Kept as one alternation so the split below preserves the original word order.
const TOKEN_RE = /(https?:\/\/[^\s<]+|www\.[^\s<]+|@[A-Za-z0-9_]{1,15}|#[\p{L}\p{N}_]+)/gu

// Trailing punctuation is almost always sentence punctuation, not part of the link.
const stripTrailing = (url) => url.replace(/[.,!?;:)\]]+$/, '')

const linkClass =
  'text-brand-secondary hover:text-brand-primary dark:hover:text-brand-secondary/80 underline underline-offset-2 break-all'

/**
 * Renders tweet text with URLs, @mentions and #hashtags turned into clickable links.
 * Mentions and hashtags resolve to x.com so they open the live profile / search.
 */
const LinkifiedText = ({ text }) => {
  if (!text) return null

  const parts = String(text).split(TOKEN_RE)

  return (
    <>
      {parts.map((part, i) => {
        if (!part) return null

        if (/^(https?:\/\/|www\.)/i.test(part)) {
          const clean = stripTrailing(part)
          const href = clean.startsWith('http') ? clean : `https://${clean}`
          return (
            <React.Fragment key={i}>
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className={linkClass}
                onClick={(e) => e.stopPropagation()}
              >
                {clean}
              </a>
              {part.slice(clean.length)}
            </React.Fragment>
          )
        }

        if (/^@[A-Za-z0-9_]{1,15}$/.test(part)) {
          return (
            <a
              key={i}
              href={`https://x.com/${part.slice(1)}`}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className={linkClass}
              onClick={(e) => e.stopPropagation()}
            >
              {part}
            </a>
          )
        }

        if (/^#/.test(part)) {
          return (
            <a
              key={i}
              href={`https://x.com/hashtag/${encodeURIComponent(part.slice(1))}`}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className={linkClass}
              onClick={(e) => e.stopPropagation()}
            >
              {part}
            </a>
          )
        }

        return <React.Fragment key={i}>{part}</React.Fragment>
      })}
    </>
  )
}

export default LinkifiedText
