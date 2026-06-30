export const TREND_LABELS: Record<string, string> = {
  improving: 'Улучшается',
  declining: 'Снижается',
  stable: 'Стабильно',
  not_enough_data: 'Недостаточно данных'
};

export const LEARNING_STATE_LABELS: Record<string, string> = {
  mastered: 'Освоенный материал',
  unstable: 'Нестабильно',
  improving: 'Есть прогресс',
  stagnant: 'Без заметного прогресса',
  not_enough_data: 'Недостаточно данных'
};

export const RISK_LEVEL_LABELS: Record<string, string> = {
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
  none: 'Риска нет',
  not_enough_data: 'Недостаточно данных'
};

export const WEAKNESS_LEVEL_LABELS: Record<string, string> = {
  high: 'Высокая',
  medium: 'Средняя',
  low: 'Низкая',
  none: 'Слабых мест не выявлено',
  not_enough_data: 'Недостаточно данных'
};

export const RECOMMENDATION_PRIORITY_LABELS: Record<string, string> = {
  high: 'Высокий',
  medium: 'Средний',
  low: 'Низкий',
  normal: 'Обычный',
  info: 'Информационный'
};

export const REASON_CODE_LABELS: Record<string, string> = {
  high_failure_rate: 'Высокая доля неудачных попыток',
  low_average: 'Низкий средний результат',
  unfinished_lessons: 'Теория изучена не полностью',
  no_progress: 'Нет заметного прогресса'
};

export function translateTrendLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Нет данных';
  }

  return TREND_LABELS[value] ?? value;
}

export function translateLearningStateLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Нет данных';
  }

  return LEARNING_STATE_LABELS[value] ?? value;
}

export function translateRiskLevelLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Нет данных';
  }

  return RISK_LEVEL_LABELS[value] ?? value;
}

export function translateWeaknessLevelLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Нет данных';
  }

  return WEAKNESS_LEVEL_LABELS[value] ?? value;
}

export function translateRecommendationPriorityLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Нет данных';
  }

  return RECOMMENDATION_PRIORITY_LABELS[value] ?? value;
}

export function translateReasonCodeLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Нет данных';
  }

  return REASON_CODE_LABELS[value] ?? value;
}
