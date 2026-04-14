import { normalizeCityName } from './region'

function normalizeText(value, fallback) {
  const text = String(value || '').trim()
  return text || fallback
}

function hashSeed(value) {
  let hash = 0
  for (const char of value) {
    hash = (hash * 31 + char.charCodeAt(0)) % 2147483647
  }
  return hash
}

function pickTwoTemplates(templates, seed) {
  if (!templates.length) return []
  const start = hashSeed(seed) % templates.length
  return [
    templates[start],
    templates[(start + 1) % templates.length],
  ]
}

function buildContext({ city, locationName }) {
  const cityLabel = normalizeText(normalizeCityName(city), '这座城市')
  const locationLabel = normalizeText(locationName, '这个角落')
  const cityPrefix = city ? `${cityLabel}的` : '这里的'
  const placeLabel = locationLabel.includes(cityLabel)
    ? locationLabel
    : `${cityLabel}·${locationLabel}`

  return {
    cityLabel,
    cityPrefix,
    locationLabel,
    placeLabel,
  }
}

const TEMPLATE_GROUPS = {
  旅行文案: {
    清新风: [
      ({ cityPrefix, placeLabel }) => `把坐标落在${placeLabel}，${cityPrefix}风和光都刚刚好，随手一拍就是很轻盈的一段旅途记忆。`,
      ({ cityLabel, locationLabel }) => `今天在${locationLabel}慢慢晃了一圈，${cityLabel}这站明亮又松弛，连心情都被照得柔软起来。`,
      ({ placeLabel }) => `路过${placeLabel}时被好天气收买，眼前的景色不喧闹，却刚好适合把喜欢认真留住。`,
    ],
    文艺风: [
      ({ placeLabel }) => `在${placeLabel}停了一会儿，风把光影吹成柔软的纹路，旅途像一页被慢慢翻开的散文。`,
      ({ cityLabel, locationLabel }) => `${cityLabel}把温柔藏进${locationLabel}的光里，走过这一站时，忽然很想把时间放慢一点。`,
      ({ placeLabel }) => `${placeLabel}像旅途中忽然亮起的一小段诗意，不用刻意寻找，站在那里就已经足够动人。`,
    ],
    日记风: [
      ({ locationLabel }) => `今天去了${locationLabel}，比想象里更舒服一点，随便走走、看看风景，心情就慢慢松开了。`,
      ({ cityLabel, placeLabel }) => `在${cityLabel}逛到${placeLabel}这一站的时候，突然觉得这趟出门很值，照片也顺手留下来了。`,
      ({ locationLabel }) => `把今天的好天气记在${locationLabel}，没有特别安排什么，但就是过得很顺、很想再来一次。`,
    ],
    '轻社交风': [
      ({ placeLabel }) => `今日份快乐坐标已送达：${placeLabel}。风景在线，心情在线，连随手拍都自带度假滤镜。`,
      ({ cityLabel, locationLabel }) => `来${cityLabel}别错过${locationLabel}，拍照很出片，散步也很舒服，属于会想二刷的一站。`,
      ({ placeLabel }) => `${placeLabel}打卡成功，景色和氛围都很能打，这一站真的很适合把好心情发出来。`,
    ],
  },
  生活记录: {
    清新风: [
      ({ placeLabel }) => `今天的日常落在${placeLabel}，空气轻轻的，节奏也慢下来了一点，刚好适合把好心情记住。`,
      ({ cityPrefix, locationLabel }) => `在${locationLabel}待了一会儿，${cityPrefix}光线很温柔，普通的一天也被照得有点可爱。`,
      ({ placeLabel }) => `${placeLabel}这段小日常很舒服，没有太多热闹，却刚刚好让人觉得放松。`,
    ],
    文艺风: [
      ({ placeLabel }) => `日常经过${placeLabel}时，光影安静地落下来，原来普通的一天也能有一点被认真收藏的意义。`,
      ({ cityLabel, locationLabel }) => `${cityLabel}的风把${locationLabel}吹得很温柔，琐碎日常忽然有了像电影片段一样的质感。`,
      ({ placeLabel }) => `把生活折成小小一页放进${placeLabel}，没有轰烈情节，却足够温柔地安放今日心绪。`,
    ],
    日记风: [
      ({ locationLabel }) => `今天在${locationLabel}待了会儿，没发生什么大事，但整个人都被这种平静安慰到了。`,
      ({ placeLabel }) => `给今天记一笔：去了${placeLabel}，拍了几张照片，也顺便把最近的疲惫放下了一点。`,
      ({ cityLabel, locationLabel }) => `在${cityLabel}的${locationLabel}过了一个很普通却挺喜欢的片刻，适合写进今天的日记里。`,
    ],
    '轻社交风': [
      ({ placeLabel }) => `今天的生活切片来自${placeLabel}，没有什么特别剧情，但氛围感已经悄悄拉满。`,
      ({ cityLabel, locationLabel }) => `${cityLabel}${locationLabel}随手记录一下，平平常常的一天，也值得发出来给自己点个赞。`,
      ({ placeLabel }) => `${placeLabel}签到，今日份轻松感拿捏住了，照片一存，心情也顺手备份成功。`,
    ],
  },
}

export function createInstantCaptions({ city, locationName, style, captionType }) {
  const typeTemplates = TEMPLATE_GROUPS[captionType] || TEMPLATE_GROUPS['旅行文案']
  const templates = typeTemplates[style] || typeTemplates['清新风']
  const context = buildContext({ city, locationName })
  const seed = `${captionType}|${style}|${city}|${locationName}`

  return pickTwoTemplates(templates, seed).map((template) => template(context))
}
