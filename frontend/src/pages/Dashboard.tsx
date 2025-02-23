import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getQuestionSets, uploadQuestions } from '../api';
import { QuestionSet } from '../types';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [questionSets, setQuestionSets] = useState<QuestionSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchQuestionSets();
  }, []);

  const fetchQuestionSets = async () => {
    try {
      const sets = await getQuestionSets();
      setQuestionSets(sets);
      setError(null);
    } catch (err) {
      setError('Failed to load question sets');
      console.error('Error fetching question sets:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setLoading(true);
      await uploadQuestions(file);
      await fetchQuestionSets(); // Refresh the list after upload
    } catch (err) {
      setError('Failed to upload file');
      console.error('Error uploading file:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-gray-800">Questionary</h1>
              </div>
            </div>
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <span className="text-gray-700">Welcome, {user?.username}!</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        <div className="px-4 py-6 sm:px-0">
          {/* Upload Section */}
          <div className="mb-8">
            <div className="border-4 border-dashed border-gray-200 rounded-lg p-8">
              <div className="text-center">
                <h2 className="text-2xl font-semibold text-gray-800 mb-4">
                  Upload your lectures
                </h2>
                <p className="mt-2 text-gray-600 mb-4">
                  Upload PDF files to generate question sets
                </p>
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
                >
                  Select PDF File
                </label>
              </div>
            </div>
          </div>

          {/* Question Sets Section */}
          <div>
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Your Question Sets</h2>
            {loading ? (
              <div className="text-center py-4">Loading...</div>
            ) : questionSets.length > 0 ? (
              <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                {questionSets.map((set) => (
                  <div
                    key={set.id}
                    className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
                  >
                    <h3 className="text-lg font-medium text-gray-900">{set.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      Questions: {set.question_count}
                    </p>
                    <p className="text-sm text-gray-500">
                      Created: {new Date(set.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-600">
                No question sets found. Upload a PDF to create your first set!
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
