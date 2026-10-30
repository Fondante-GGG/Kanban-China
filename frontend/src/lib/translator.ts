import * as OpenCC from 'opencc-js';
import { LanguageCode } from '@/types';

// Initialize OpenCC converters
const s2tConverter = typeof window !== 'undefined' || typeof global !== 'undefined'
  ? OpenCC.Converter({ from: 'cn', to: 'tw' })
  : (t: string) => t;

const t2sConverter = typeof window !== 'undefined' || typeof global !== 'undefined'
  ? OpenCC.Converter({ from: 'tw', to: 'cn' })
  : (t: string) => t;

/**
 * Convert any Simplified Chinese text to Traditional Chinese (Taiwan/Hong Kong standard)
 */
export function toTraditionalChinese(text: string): string {
  if (!text) return '';
  try {
    return s2tConverter(text);
  } catch {
    return text;
  }
}

/**
 * Convert any Traditional Chinese text to Simplified Chinese
 */
export function toSimplifiedChinese(text: string): string {
  if (!text) return '';
  try {
    return t2sConverter(text);
  } catch {
    return text;
  }
}

// Known full names with roles and clean Chinese translations
const KNOWN_PERSON_NAMES: Record<string, { zh: string; ky?: string }> = {
  'Асанов Асан Асанович (Гендиректор)': { zh: '阿萨诺夫·阿桑 (总经理)', ky: 'Асанов Асан (Башкы директор)' },
  'Асанов Асан Асанович': { zh: '阿萨诺夫·阿桑', ky: 'Асанов Асан' },
  'Асанов Асан': { zh: '阿萨诺夫·阿桑', ky: 'Асанов Асан' },
  'Иванов Иван Иванович (Тимлид IT)': { zh: '伊万诺夫·伊万 (IT主管)', ky: 'Иванов Иван (IT башчысы)' },
  'Иванов Иван Иванович': { zh: '伊万诺夫·伊万', ky: 'Иванов Иван' },
  'Иванов Иван': { zh: '伊万诺夫·伊万', ky: 'Иванов Иван' },
  'Бектур Садыков (Senior Dev)': { zh: '别克图尔·萨德科夫 (高级开发人员)', ky: 'Бектур Садыков (Улук иштеп чыгуучу)' },
  'Бектур Садыков': { zh: '别克图尔·萨德科夫', ky: 'Бектур Садыков' },
  'Ли Вэй / Li Wei (Руководитель маркетинга)': { zh: '李伟 (营销主管)', ky: 'Ли Вэй (Маркетинг жетекчиси)' },
  'Ли Вэй / Li Wei': { zh: '李伟', ky: 'Ли Вэй' },
  'Ли Вэй': { zh: '李伟', ky: 'Ли Вэй' },
  'Li Wei': { zh: '李伟', ky: 'Ли Вэй' },
  'Айпери Жумабекова (SMM / PR)': { zh: '艾佩里·茹马别科娃 (SMM/公关专员)', ky: 'Айпери Жумабекова (SMM / PR)' },
  'Айпери Жумабекова': { zh: '艾佩里·茹马别科娃', ky: 'Айпери Жумабекова' },
  'Зухра Эже': { zh: '祖赫拉·埃热 (系统管理员)', ky: 'Зухра Эже (Системалык админ)' },
  'Петров Петр': { zh: '彼得罗夫·彼得', ky: 'Петров Петр' },
  'Смирнов Сергей': { zh: '斯米尔诺夫·谢尔盖', ky: 'Смирнов Сергей' },
  'Сидорова Анна': { zh: '西多罗娃·安娜', ky: 'Сидорова Анна' },
  'Кузнецова Елена': { zh: '库兹涅佐娃·叶莲娜', ky: 'Кузнецова Елена' },
};

// Known department translations
const KNOWN_DEPARTMENTS: Record<string, { zh: string; ky?: string }> = {
  'IT & Разработка': { zh: 'IT与研发部', ky: 'IT жана программалоо бөлүмү' },
  'IT & разработка': { zh: 'IT与研发部', ky: 'IT жана программалоо бөлүмү' },
  'Маркетинг & PR': { zh: '市场营销与公关部', ky: 'Маркетинг жана PR бөлүмү' },
  'маркетинг & pr': { zh: '市场营销与公关部', ky: 'Маркетинг жана PR бөлүмү' },
  'Финансы и Бухгалтерия': { zh: '财务与会计部', ky: 'Каржы жана бухгалтерия бөлүмү' },
  'финансы и бухгалтерия': { zh: '财务与会计部', ky: 'Каржы жана бухгалтерия бөлүмү' },
  'Отдел логистики и снабжения': { zh: '物流与供应部', ky: 'Логистика жана камсыздоо бөлүмү' },
  'отдел логистики и снабжения': { zh: '物流与供应部', ky: 'Логистика жана камсыздоо бөлүмү' },
  'Склад': { zh: '仓储物流部', ky: 'Кампа бөлүмү' },
  'склад': { zh: '仓储物流部', ky: 'Кампа бөлүмү' },
};

// Known board translations
const KNOWN_BOARDS: Record<string, { zh: string; ky?: string }> = {
  'Разработка платформы Kanban': { zh: '看板平台系统研发', ky: 'Канбан платформасын иштеп чыгуу' },
  'Запуск рекламной кампании Q4': { zh: '第四季度广告营销活动', ky: 'Q4 жарнак кампаниясын баштоо' },
  'Годовой финансовый аудит': { zh: '年度财务合规审计', ky: 'Жылдык каржылык аудит' },
  'Отдел логистики и снабжения': { zh: '物流与供应管理看板', ky: 'Логистика жана камсыздоо тактасы' },
  'Склад': { zh: '仓储与库存管理看板', ky: 'Кампа башкаруу тактасы' },
  'склад': { zh: '仓储与库存管理看板', ky: 'Кампа башкаруу тактасы' },
};

// Known general terms and activity phrases
const PHRASE_DICTIONARY: Record<string, { zh: string; ky?: string }> = {
  // Roles
  'Генеральный директор': { zh: '总经理', ky: 'Башкы директор' },
  'Гендиректор': { zh: '总经理', ky: 'Башкы директор' },
  'Руководитель отдела': { zh: '部门主管', ky: 'Бөлүм башчысы' },
  'Руководитель': { zh: '部门主管', ky: 'Жетекчи' },
  'Сотрудник': { zh: '员工', ky: 'Кызматкер' },
  'Тимлид IT': { zh: 'IT技术主管', ky: 'IT тимлид' },
  'Senior Dev': { zh: '高级工程师', ky: 'Улук иштеп чыгуучу' },
  'Руководитель маркетинга': { zh: '市场部主管', ky: 'Маркетинг жетекчиси' },
  'SMM / PR': { zh: '社媒与公关专员', ky: 'SMM жана PR адиси' },
  'Бухгалтер': { zh: '会计主管', ky: 'Башкы бухгалтер' },
  'Разработчик': { zh: '开发工程师', ky: 'Программист' },
  'Бэкенд': { zh: '后端开发工程师', ky: 'Бэкенд иштеп чыгуучу' },
  'Маркетолог': { zh: '营销专员', ky: 'Маркетолог' },

  // Statuses
  'Активен': { zh: '正常活跃', ky: 'Активдүү' },
  'Заблокирован': { zh: '已冻结停用', ky: 'Бөгөттөлгөн' },
  'Просрочено': { zh: '已逾期', ky: 'Мөөнөтү өткөн' },
  'Просрочена': { zh: '已逾期', ky: 'Мөөнөтү өткөн' },
  'Выполнено': { zh: '已完成', ky: 'Аткарылды' },
  'В процессе': { zh: '处理中', ky: 'Аткарылууда' },
  'На проверке': { zh: '待审核', ky: 'Текшерүүдө' },
  'Нужно сделать': { zh: '待办任务', ky: 'Керектүү иштер' },
  'Баги': { zh: '缺陷排查', ky: 'Мүчүлүштүктөр' },

  // Priority
  'Срочный': { zh: '紧急', ky: 'Тез арада' },
  'Высокий': { zh: '高优先级', ky: 'Жогорку' },
  'Средний': { zh: '普通中级', ky: 'Орто' },
  'Низкий': { zh: '低优先级', ky: 'Төмөн' },

  // Common activities
  'создал(а) карточку': { zh: '创建了任务卡片', ky: 'тапшырма түздү' },
  'создана карточка': { zh: '创建了任务卡片', ky: 'тапшырма түзүлдү' },
  'переместил(а) в колонку': { zh: '移动任务至列', ky: 'тилкеге жылдырды' },
  'перемещена в колонку': { zh: '移动任务至列', ky: 'тилкеге жылдырылды' },
  'добавил(а) комментарий': { zh: '发表了新评论', ky: 'пикир кошту' },
  'обновил(а) карточку': { zh: '更新了任务详情', ky: 'тапшырманы жаңалады' },
  'прикрепил(а) файл': { zh: '上传了相关文件附件', ky: 'файл тиркеди' },
  'добавил(а) пункт чек-листа': { zh: '添加了检查清单子项', ky: 'текшерүү пунктун кошту' },
  'отметил(а) выполненным': { zh: '标记检查项为已完成', ky: 'аткарылды деп белгиледи' },

  // Finance notifications
  'Новая заявка на расход': { zh: '新的费用申请', ky: 'Жаңы чыгым арызы' },
  'Статус расхода изменён': { zh: '费用状态已更新', ky: 'Чыгымдын абалы өзгөртүлдү' },
  'Возмещение выплачено': { zh: '报销已支付', ky: 'Компенсация төлөндү' },
  'отправил(а) расход': { zh: '提交了费用申请', ky: 'чыгым арызын жөнөттү' },
  'на сумму': { zh: '金额为', ky: 'суммасы' },
  'Заявка': { zh: '申请', ky: 'Арыз' },
  'Черновик': { zh: '草稿', ky: 'Черновик' },
  'Нужны уточнения': { zh: '需要补充信息', ky: 'Тактоо керек' },
  'Согласовано': { zh: '已批准', ky: 'Бекитилди' },
  'Отклонено': { zh: '已拒绝', ky: 'Четке кагылды' },
  'Выплачено': { zh: '已支付', ky: 'Төлөндү' },

  // Attendance notifications
  'Приход сотрудника в офис': { zh: '员工到达办公室打卡', ky: 'Кызматкер офиске келди' },
  'пришёл(ла) в офис': { zh: '已到达办公室', ky: 'офиске келди' },
  'отметил(а) приход в офис': { zh: '已打卡到达办公室', ky: 'офиске келгенин белгиледи' },
  'отметил(а) приход': { zh: '已打卡签到', ky: 'келгенин белгиледи' },
};

// Standard Russian-Chinese Xinhua transliteration table for syllables
const CYRILLIC_SYLLABLES: [string, string][] = [
  ['алексей', '亚历克塞'], ['сергей', '谢尔盖'], ['дмитрий', '德米特里'],
  ['владимир', '弗拉基米尔'], ['михаил', '米哈伊尔'], ['андрей', '安德烈'],
  ['александр', '亚历山大'], ['николай', '尼古拉'], ['максим', '马克西姆'],
  ['иван', '伊万'], ['петр', '彼得'], ['павел', '帕维尔'],
  ['асан', '阿桑'], ['бектүр', '别克图尔'], ['бектур', '别克图尔'],
  ['нурлан', '努尔兰'], ['айбек', '艾别克'], ['дастан', '达斯坦'],
  ['азамат', '阿扎马特'], ['чыңгыз', '钦吉斯'], ['чынгыз', '钦吉斯'],
  ['айпери', '艾佩里'], ['зухра', '祖赫拉'], ['елена', '叶莲娜'],
  ['анна', '安娜'], ['ольга', '奥尔加'], ['мария', '玛丽亚'],
  ['татьяна', '塔季扬娜'], ['наталья', '娜塔莉亚'], ['светлана', '斯韦特兰娜'],
  ['садыков', '萨德科夫'], ['асанов', '阿萨诺夫'], ['жумабеков', '茹马别科夫'],
  ['иванов', '伊万诺夫'], ['петров', '彼得罗夫'], ['сидоров', '西多罗夫'],
  ['смирнов', '斯米尔诺夫'], ['кузнецов', '库兹涅佐夫'], ['попов', '波波夫'],
  ['васильев', '瓦西里耶夫'], ['соколов', '索科洛夫'], ['михайлов', '米哈伊洛夫'],
  ['новиков', '诺维科夫'], ['федоров', '费多罗夫'], ['морозов', '莫罗佐夫'],
  ['волков', '沃尔科夫'], ['алексеев', '阿列克谢耶夫'], ['лебедев', '列别杰夫'],
  ['семенов', '谢苗诺夫'], ['павлов', '帕夫洛夫'], ['козлов', '科兹洛夫'],
  ['степанов', '斯捷潘诺夫'], ['николаев', '尼古拉耶夫'], ['орлов', '奥尔洛夫'],
  ['андреев', '安德烈耶夫'], ['макаров', '马卡罗夫'], ['никитин', '尼基京'],
  ['захаров', '扎哈罗夫'], ['зайцев', '扎伊采夫'], ['соловьев', '索洛维约夫'],
  ['борисов', '鲍里索夫'], ['яковлев', '雅科夫列夫'],
  ['ович', '诺维奇'], ['евич', '耶维奇'], ['ична', '伊奇娜'],
  ['овна', '奥夫娜'], ['евна', '耶夫娜'], ['ова', '奥娃'],
  ['ева', '耶娃'], ['ина', '因娜'], ['ский', '斯基'], ['ская', '斯卡娅'],
  ['ба', '巴'], ['бе', '贝'], ['би', '比'], ['бо', '博'], ['бу', '布'],
  ['ва', '瓦'], ['ве', '韦'], ['ви', '维'], ['во', '沃'], ['ву', '武'],
  ['га', '加'], ['ге', '格'], ['ги', '吉'], ['го', '戈'], ['гу', '古'],
  ['да', '达'], ['де', '杰'], ['ди', '迪'], ['до', '多'], ['ду', '杜'],
  ['жа', '扎'], ['же', '热'], ['жи', '日'], ['жо', '若'], ['жу', '茹'],
  ['за', '扎'], ['зе', '泽'], ['зи', '齐'], ['зо', '佐'], ['зу', '祖'],
  ['ка', '卡'], ['ке', '克'], ['ки', '基'], ['ко', '科'], ['ку', '库'],
  ['ла', '拉'], ['ле', '列'], ['ли', '利'], ['ло', '洛'], ['лу', '卢'],
  ['ма', '马'], ['ме', '梅'], ['ми', '米'], ['мо', '莫'], ['му', '穆'],
  ['на', '纳'], ['не', '内'], ['ни', '尼'], ['но', '诺'], ['ну', '努'],
  ['па', '帕'], ['пе', '佩'], ['пи', '皮'], ['по', '波'], ['пу', '普'],
  ['ра', '拉'], ['ре', '雷'], ['ри', '里'], ['ро', '罗'], ['ру', '鲁'],
  ['са', '萨'], ['се', '塞'], ['си', '西'], ['со', '索'], ['су', '苏'],
  ['та', '塔'], ['те', '捷'], ['ти', '季'], ['то', '托'], ['ту', '图'],
  ['фа', '法'], ['фе', '费'], ['фи', '菲'], ['фо', '福'], ['фу', '富'],
  ['ха', '哈'], ['хе', '海'], ['хи', '希'], ['хо', '霍'], ['ху', '胡'],
  ['ца', '查'], ['це', '采'], ['ци', '茨'], ['цо', '佐'], ['цу', '楚'],
  ['ча', '查'], ['че', '切'], ['чи', '奇'], ['чо', '乔'], ['чу', '丘'],
  ['ша', '沙'], ['ше', '舍'], ['ши', '希'], ['шо', '绍'], ['шу', '舒'],
  ['а', '阿'], ['б', '布'], ['в', '夫'], ['г', '格'], ['д', '德'],
  ['е', '叶'], ['ё', '约'], ['ж', '日'], ['з', '兹'], ['и', '伊'],
  ['й', '伊'], ['к', '克'], ['л', '尔'], ['м', '姆'], ['н', '恩'],
  ['о', '奥'], ['п', '普'], ['р', '尔'], ['с', '斯'], ['т', '特'],
  ['у', '乌'], ['ф', '夫'], ['х', '赫'], ['ц', '茨'], ['ч', '奇'],
  ['ш', '什'], ['щ', '希'], ['ъ', ''], ['ы', '伊'], ['ь', ''],
  ['э', '埃'], ['ю', '尤'], ['я', '亚'], ['ө', '厄'], ['ү', '于'], ['ң', '恩']
];

/**
 * Phonetically transliterates any unknown Cyrillic name to Chinese characters
 */
function transliterateCyrillicNameToChinese(name: string): string {
  if (!name || !name.trim()) return '';

  // Extract roles in parentheses, e.g. " (Гендиректор)"
  const roleMatch = name.match(/\((.*?)\)/);
  let cleanName = name;
  let translatedRole = '';

  if (roleMatch) {
    cleanName = name.replace(/\(.*?\)/, '').trim();
    const rawRole = roleMatch[1].trim();
    if (PHRASE_DICTIONARY[rawRole]) {
      translatedRole = ` (${PHRASE_DICTIONARY[rawRole].zh})`;
    } else {
      translatedRole = ` (${rawRole})`;
    }
  }

  // Check known names
  if (KNOWN_PERSON_NAMES[cleanName]) {
    return KNOWN_PERSON_NAMES[cleanName].zh + translatedRole;
  }

  // Tokenize words (e.g. "Асанов", "Асан", "Асанович")
  const parts = cleanName.split(/\s+/).filter(Boolean);
  const zhParts = parts.map((part) => {
    const lower = part.toLowerCase();
    let res = '';
    let i = 0;
    while (i < lower.length) {
      let matched = false;
      for (const [pattern, zh] of CYRILLIC_SYLLABLES) {
        if (lower.startsWith(pattern, i)) {
          res += zh;
          i += pattern.length;
          matched = true;
          break;
        }
      }
      if (!matched) {
        res += lower[i];
        i++;
      }
    }
    return res;
  });

  return zhParts.join('·') + translatedRole;
}

/**
 * Localize an employee's full name based on selected language
 */
export function localizePersonName(name: string | undefined | null, lang: LanguageCode): string {
  if (!name) return '';
  if (lang === 'ru') return name;

  if (KNOWN_PERSON_NAMES[name]) {
    if (lang === 'ky') return KNOWN_PERSON_NAMES[name].ky || name;
    if (lang === 'zh-Hant') return toTraditionalChinese(KNOWN_PERSON_NAMES[name].zh);
    if (lang === 'zh-Hans') return KNOWN_PERSON_NAMES[name].zh;
  }

  // Handle generic Cyrillic name transliteration for Chinese
  if (lang === 'zh-Hans') {
    return transliterateCyrillicNameToChinese(name);
  }
  if (lang === 'zh-Hant') {
    return toTraditionalChinese(transliterateCyrillicNameToChinese(name));
  }

  return name;
}

/**
 * Localize department name
 */
export function localizeDepartmentName(name: string | undefined | null, lang: LanguageCode): string {
  if (!name) return '';
  if (lang === 'ru') return name;

  const trimmed = name.trim();
  if (KNOWN_DEPARTMENTS[trimmed]) {
    if (lang === 'ky') return KNOWN_DEPARTMENTS[trimmed].ky || trimmed;
    if (lang === 'zh-Hant') return toTraditionalChinese(KNOWN_DEPARTMENTS[trimmed].zh);
    if (lang === 'zh-Hans') return KNOWN_DEPARTMENTS[trimmed].zh;
  }

  // Fallback for custom departments
  if (lang === 'zh-Hans') {
    if (trimmed.startsWith('Отдел ')) {
      return transliterateCyrillicNameToChinese(trimmed.replace('Отдел ', '')) + '部';
    }
    return transliterateCyrillicNameToChinese(trimmed);
  }
  if (lang === 'zh-Hant') {
    if (trimmed.startsWith('Отдел ')) {
      return toTraditionalChinese(transliterateCyrillicNameToChinese(trimmed.replace('Отдел ', '')) + '部');
    }
    return toTraditionalChinese(transliterateCyrillicNameToChinese(trimmed));
  }

  return name;
}

/**
 * Localize board title
 */
export function localizeBoardTitle(title: string | undefined | null, lang: LanguageCode, deptName?: string | null): string {
  if (!title) return '';
  if (lang === 'ru') return title;

  const trimmed = title.trim();
  if (KNOWN_BOARDS[trimmed]) {
    if (lang === 'ky') return KNOWN_BOARDS[trimmed].ky || trimmed;
    if (lang === 'zh-Hant') return toTraditionalChinese(KNOWN_BOARDS[trimmed].zh);
    if (lang === 'zh-Hans') return KNOWN_BOARDS[trimmed].zh;
  }

  // Check department name match
  if (deptName && KNOWN_DEPARTMENTS[deptName]) {
    if (trimmed.toLowerCase() === deptName.toLowerCase() || trimmed.toLowerCase() === `доска: ${deptName.toLowerCase()}`) {
      return localizeDepartmentName(deptName, lang);
    }
  }

  if (KNOWN_DEPARTMENTS[trimmed]) {
    return localizeDepartmentName(trimmed, lang);
  }

  if (lang === 'zh-Hans') {
    return transliterateCyrillicNameToChinese(trimmed);
  }
  if (lang === 'zh-Hant') {
    return toTraditionalChinese(transliterateCyrillicNameToChinese(trimmed));
  }

  return title;
}

/**
 * Localize role title
 */
export function localizeRole(role: string | undefined | null, lang: LanguageCode): string {
  if (!role) return '';
  if (role === 'general_director') {
    if (lang === 'ky') return 'Башкы директор';
    if (lang === 'zh-Hant') return '總經理';
    if (lang === 'zh-Hans') return '总经理';
    return 'Генеральный директор';
  }
  if (role === 'manager') {
    if (lang === 'ky') return 'Бөлүм башчысы';
    if (lang === 'zh-Hant') return '部門主管';
    if (lang === 'zh-Hans') return '部门主管';
    return 'Руководитель отдела';
  }
  if (role === 'employee') {
    if (lang === 'ky') return 'Кызматкер';
    if (lang === 'zh-Hant') return '員工';
    if (lang === 'zh-Hans') return '员工';
    return 'Сотрудник';
  }
  if (role === 'accountant') {
    if (lang === 'ky') return 'Бухгалтер';
    if (lang === 'zh-Hant') return '會計';
    if (lang === 'zh-Hans') return '会计';
    return 'Бухгалтер';
  }

  // Check phrase dictionary
  if (PHRASE_DICTIONARY[role]) {
    if (lang === 'ky') return PHRASE_DICTIONARY[role].ky || role;
    if (lang === 'zh-Hant') return toTraditionalChinese(PHRASE_DICTIONARY[role].zh);
    if (lang === 'zh-Hans') return PHRASE_DICTIONARY[role].zh;
  }

  return role;
}

/**
 * Localize dynamic text (checklist items, actions, notifications, status)
 */
export function localizeDynamicText(text: string | undefined | null, lang: LanguageCode): string {
  if (!text) return '';
  if (lang === 'ru') return text;

  const trimmed = text.trim();

  // Exact phrase match
  if (PHRASE_DICTIONARY[trimmed]) {
    if (lang === 'ky') return PHRASE_DICTIONARY[trimmed].ky || trimmed;
    if (lang === 'zh-Hant') return toTraditionalChinese(PHRASE_DICTIONARY[trimmed].zh);
    if (lang === 'zh-Hans') return PHRASE_DICTIONARY[trimmed].zh;
  }

  // Substring phrase replacement
  let res = trimmed;
  for (const [ruKey, tr] of Object.entries(PHRASE_DICTIONARY)) {
    if (res.includes(ruKey)) {
      const rep = lang === 'ky' ? (tr.ky || ruKey) : tr.zh;
      res = res.split(ruKey).join(rep);
    }
  }

  if (lang === 'zh-Hant') {
    return toTraditionalChinese(res);
  }
  if (lang === 'zh-Hans') {
    return toSimplifiedChinese(res);
  }

  return res;
}
