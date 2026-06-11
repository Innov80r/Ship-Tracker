/* Country code → emoji flag */
const FLAG_EMOJIS = {}

export function getFlagEmoji(isoCode) {
  if (!isoCode || isoCode.length !== 2) return '🏳️'
  return String.fromCodePoint(...[...isoCode.toUpperCase()].map(c => 0x1F1E6 + c.charCodeAt(0) - 65))
}

export default getFlagEmoji
