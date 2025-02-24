export interface Question {
  id: number;
  question_text: string;
  options: string[];
  correct_answer: string;
  source_lecture?: string;
  page_range?: string;
  set_id: number;
}

export interface QuestionSet {
  id: number;
  name: string;
  question_count: number;
  created_at: string;
}

export interface QuizResult {
  score: number;
  total: number;
  results: Array<{
    question: string;
    user_answer: string;
    correct_answer: string;
    is_correct: boolean;
    options: string[];
  }>;
  incorrect_answers: Record<string, {
    question: string;
    user_answer: string;
    correct_answer: string;
    options: string[];
  }>;
  has_incorrect: boolean;
}

export interface ReviewResult {
  score: number;
  total: number;
  results: Array<{
    question: string;
    user_answer: string;
    correct_answer: string;
    is_correct: boolean;
    options: string[];
  }>;
  still_incorrect: Array<{
    id: number;
    question: string;
    correct_answer: string;
    options: string[];
  }>;
  has_incorrect: boolean;
}
