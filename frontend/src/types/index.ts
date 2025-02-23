export interface Question {
  id: number;
  question: string;
  options: string[];
  correct_answer?: string;
  set_id: number;
}

export interface QuestionSet {
  id: number;
  name: string;
}

export interface QuizResult {
  score: number;
  total: number;
  correct_answers: Record<string, string>;
  incorrect_answers: Record<string, string>;
  selected_answers: Record<string, string>;
}

export interface ReviewResult {
  score: number;
  total: number;
  correct_answers: Record<string, string>;
  incorrect_answers: Record<string, string>;
  selected_answers: Record<string, string>;
}

export interface UploadProgress {
  status: string;
  message: string;
  percent: number;
}
