import React, { useState, useEffect } from 'react';
import {
  QuestionMarkCircleIcon,
  BookOpenIcon,
  VideoCameraIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  ClockIcon,
  StarIcon,
  UserIcon,
  TagIcon,
  LinkIcon,
  PlayIcon,
} from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';

interface HelpArticle {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  readTime: number;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  lastUpdated: Date;
  helpful: number;
  views: number;
}

interface FAQ {
  id: string;
  question: string;
  answer: string;
  category: string;
  helpful: number;
}

interface VideoTutorial {
  id: string;
  title: string;
  description: string;
  duration: string;
  thumbnail: string;
  category: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
}

const LightweightHelpCenter: React.FC = () => {
  const { addNotification } = useNotification();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [activeSection, setActiveSection] = useState('overview');
  const [expandedFAQ, setExpandedFAQ] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const categories = [
    { id: 'all', name: 'All Topics', icon: BookOpenIcon },
    { id: 'getting-started', name: 'Getting Started', icon: PlayIcon },
    { id: 'collections', name: 'Collections', icon: DocumentTextIcon },
    { id: 'search', name: 'Search & RAG', icon: MagnifyingGlassIcon },
    { id: 'administration', name: 'Administration', icon: UserIcon },
    { id: 'troubleshooting', name: 'Troubleshooting', icon: QuestionMarkCircleIcon },
  ];

  const sections = [
    { id: 'overview', name: 'Overview', icon: BookOpenIcon },
    { id: 'articles', name: 'Articles', icon: DocumentTextIcon },
    { id: 'faqs', name: 'FAQs', icon: QuestionMarkCircleIcon },
    { id: 'videos', name: 'Video Tutorials', icon: VideoCameraIcon },
    { id: 'contact', name: 'Contact Support', icon: ChatBubbleLeftRightIcon },
  ];

  const [articles, setArticles] = useState<HelpArticle[]>([]);
  const [faqs, setFaqs] = useState<FAQ[]>([]);
  const [videos, setVideos] = useState<VideoTutorial[]>([]);

  useEffect(() => {
    loadHelpData();
  }, []);

  const loadHelpData = async () => {
    setIsLoading(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));

      const mockArticles: HelpArticle[] = [
        {
          id: '1',
          title: 'Getting Started with RAG Modulo',
          content: 'Learn the basics of setting up and using RAG Modulo for your document processing needs.',
          category: 'getting-started',
          tags: ['setup', 'basics', 'tutorial'],
          readTime: 5,
          difficulty: 'beginner',
          lastUpdated: new Date('2024-01-10'),
          helpful: 45,
          views: 234,
        },
        {
          id: '2',
          title: 'Creating and Managing Collections',
          content: 'Step-by-step guide to creating document collections and organizing your content.',
          category: 'collections',
          tags: ['collections', 'organization', 'documents'],
          readTime: 8,
          difficulty: 'beginner',
          lastUpdated: new Date('2024-01-08'),
          helpful: 32,
          views: 189,
        },
        {
          id: '3',
          title: 'Advanced Search Techniques',
          content: 'Master the art of semantic search and retrieval-augmented generation.',
          category: 'search',
          tags: ['search', 'rag', 'semantic'],
          readTime: 12,
          difficulty: 'advanced',
          lastUpdated: new Date('2024-01-05'),
          helpful: 28,
          views: 156,
        },
        {
          id: '4',
          title: 'User Management and Permissions',
          content: 'Configure user access, roles, and permissions in your RAG Modulo instance.',
          category: 'administration',
          tags: ['users', 'permissions', 'admin'],
          readTime: 10,
          difficulty: 'intermediate',
          lastUpdated: new Date('2024-01-03'),
          helpful: 21,
          views: 98,
        },
        {
          id: '5',
          title: 'Troubleshooting Common Issues',
          content: 'Solutions to frequently encountered problems and error messages.',
          category: 'troubleshooting',
          tags: ['troubleshooting', 'errors', 'fixes'],
          readTime: 7,
          difficulty: 'intermediate',
          lastUpdated: new Date('2024-01-01'),
          helpful: 38,
          views: 203,
        },
      ];

      const mockFAQs: FAQ[] = [
        {
          id: '1',
          question: 'How do I upload documents to a collection?',
          answer: 'You can upload documents by navigating to your collection, clicking the "Add Documents" button, and either dragging files or selecting them from your computer. Supported formats include PDF, DOCX, TXT, and MD files.',
          category: 'collections',
          helpful: 67,
        },
        {
          id: '2',
          question: 'What is the maximum file size for uploads?',
          answer: 'The default maximum file size is 100MB per file. This can be configured by your system administrator in the system settings.',
          category: 'collections',
          helpful: 43,
        },
        {
          id: '3',
          question: 'How does semantic search work?',
          answer: 'Semantic search uses vector embeddings to understand the meaning of your query and find relevant content based on context rather than just keyword matching. This allows for more intelligent and accurate search results.',
          category: 'search',
          helpful: 52,
        },
        {
          id: '4',
          question: 'Can I integrate with external APIs?',
          answer: 'Yes, RAG Modulo supports integration with various LLM providers including OpenAI, Anthropic, and IBM WatsonX. You can configure these in the system settings.',
          category: 'administration',
          helpful: 29,
        },
        {
          id: '5',
          question: 'Why are my search results not relevant?',
          answer: 'Poor search results can be caused by insufficient document indexing, improper collection setup, or misconfigured embedding models. Check your collection status and ensure documents are properly processed.',
          category: 'troubleshooting',
          helpful: 35,
        },
      ];

      const mockVideos: VideoTutorial[] = [
        {
          id: '1',
          title: 'RAG Modulo Quick Start Guide',
          description: 'Get up and running with RAG Modulo in under 10 minutes.',
          duration: '9:42',
          thumbnail: '/placeholder-video.jpg',
          category: 'getting-started',
          difficulty: 'beginner',
        },
        {
          id: '2',
          title: 'Building Your First Collection',
          description: 'Learn how to create and populate document collections.',
          duration: '15:23',
          thumbnail: '/placeholder-video.jpg',
          category: 'collections',
          difficulty: 'beginner',
        },
        {
          id: '3',
          title: 'Advanced RAG Techniques',
          description: 'Deep dive into retrieval-augmented generation strategies.',
          duration: '28:15',
          thumbnail: '/placeholder-video.jpg',
          category: 'search',
          difficulty: 'advanced',
        },
        {
          id: '4',
          title: 'System Administration Best Practices',
          description: 'Configure and maintain your RAG Modulo deployment.',
          duration: '22:07',
          thumbnail: '/placeholder-video.jpg',
          category: 'administration',
          difficulty: 'intermediate',
        },
      ];

      setArticles(mockArticles);
      setFaqs(mockFAQs);
      setVideos(mockVideos);
    } catch (error) {
      addNotification('error', 'Loading Error', 'Failed to load help content.');
    } finally {
      setIsLoading(false);
    }
  };

  const filteredArticles = articles.filter(article => {
    const matchesCategory = activeCategory === 'all' || article.category === activeCategory;
    const matchesSearch = !searchQuery ||
      article.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      article.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      article.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const filteredFAQs = faqs.filter(faq => {
    const matchesCategory = activeCategory === 'all' || faq.category === activeCategory;
    const matchesSearch = !searchQuery ||
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const filteredVideos = videos.filter(video => {
    const matchesCategory = activeCategory === 'all' || video.category === activeCategory;
    const matchesSearch = !searchQuery ||
      video.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      video.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner': return 'text-green-50 bg-green-10';
      case 'intermediate': return 'text-yellow-30 bg-yellow-10';
      case 'advanced': return 'text-red-50 bg-red-10';
      default: return 'text-gray-70 bg-gray-10';
    }
  };

  const markHelpful = (type: 'article' | 'faq', id: string) => {
    if (type === 'article') {
      setArticles(prev => prev.map(article =>
        article.id === id ? { ...article, helpful: article.helpful + 1 } : article
      ));
    } else {
      setFaqs(prev => prev.map(faq =>
        faq.id === id ? { ...faq, helpful: faq.helpful + 1 } : faq
      ));
    }
    addNotification('success', 'Thank You!', 'Your feedback helps us improve.');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-60 mx-auto mb-4"></div>
          <p className="text-gray-70">Loading help center...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-10 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-gray-100 mb-4">Help Center</h1>
          <p className="text-gray-70 mb-6">Find answers, tutorials, and resources to get the most out of RAG Modulo</p>

          {/* Search */}
          <div className="max-w-2xl mx-auto relative">
            <MagnifyingGlassIcon className="w-5 h-5 absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-60" />
            <input
              type="text"
              placeholder="Search help articles, FAQs, and tutorials..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field w-full pl-12 py-4 text-lg"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Navigation */}
            <div className="card p-4">
              <nav className="space-y-1">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    className={`w-full flex items-center space-x-3 px-3 py-2 text-sm font-medium rounded-md ${
                      activeSection === section.id
                        ? 'bg-blue-60 text-white'
                        : 'text-gray-70 hover:text-gray-100 hover:bg-gray-20'
                    }`}
                  >
                    <section.icon className="w-4 h-4" />
                    <span>{section.name}</span>
                  </button>
                ))}
              </nav>
            </div>

            {/* Categories */}
            <div className="card p-4">
              <h3 className="text-sm font-medium text-gray-100 mb-3">Categories</h3>
              <nav className="space-y-1">
                {categories.map((category) => (
                  <button
                    key={category.id}
                    onClick={() => setActiveCategory(category.id)}
                    className={`w-full flex items-center space-x-3 px-2 py-1 text-sm rounded-md ${
                      activeCategory === category.id
                        ? 'bg-blue-10 text-blue-60'
                        : 'text-gray-70 hover:text-gray-100 hover:bg-gray-10'
                    }`}
                  >
                    <category.icon className="w-4 h-4" />
                    <span>{category.name}</span>
                  </button>
                ))}
              </nav>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {/* Overview */}
            {activeSection === 'overview' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="card p-6 text-center">
                    <div className="w-12 h-12 mx-auto mb-4 bg-blue-10 rounded-full flex items-center justify-center">
                      <DocumentTextIcon className="w-6 h-6 text-blue-60" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-100 mb-2">Documentation</h3>
                    <p className="text-gray-70 mb-4">Comprehensive guides and tutorials</p>
                    <button
                      onClick={() => setActiveSection('articles')}
                      className="btn-primary"
                    >
                      Browse Articles
                    </button>
                  </div>

                  <div className="card p-6 text-center">
                    <div className="w-12 h-12 mx-auto mb-4 bg-green-10 rounded-full flex items-center justify-center">
                      <QuestionMarkCircleIcon className="w-6 h-6 text-green-60" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-100 mb-2">FAQs</h3>
                    <p className="text-gray-70 mb-4">Frequently asked questions</p>
                    <button
                      onClick={() => setActiveSection('faqs')}
                      className="btn-primary"
                    >
                      View FAQs
                    </button>
                  </div>

                  <div className="card p-6 text-center">
                    <div className="w-12 h-12 mx-auto mb-4 bg-purple-10 rounded-full flex items-center justify-center">
                      <VideoCameraIcon className="w-6 h-6 text-purple-60" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-100 mb-2">Video Tutorials</h3>
                    <p className="text-gray-70 mb-4">Step-by-step video guides</p>
                    <button
                      onClick={() => setActiveSection('videos')}
                      className="btn-primary"
                    >
                      Watch Videos
                    </button>
                  </div>
                </div>

                <div className="card p-6">
                  <h2 className="text-xl font-semibold text-gray-100 mb-4">Popular Articles</h2>
                  <div className="space-y-3">
                    {articles.slice(0, 5).map((article) => (
                      <div key={article.id} className="flex items-center justify-between p-3 border border-gray-20 rounded-lg hover:bg-gray-10">
                        <div className="flex-1">
                          <h3 className="font-medium text-gray-100 mb-1">{article.title}</h3>
                          <div className="flex items-center space-x-4 text-sm text-gray-60">
                            <span className="flex items-center space-x-1">
                              <ClockIcon className="w-3 h-3" />
                              <span>{article.readTime} min read</span>
                            </span>
                            <span className="flex items-center space-x-1">
                              <StarIcon className="w-3 h-3" />
                              <span>{article.helpful} helpful</span>
                            </span>
                          </div>
                        </div>
                        <ChevronRightIcon className="w-4 h-4 text-gray-60" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Articles */}
            {activeSection === 'articles' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-100">Help Articles</h2>
                  <span className="text-sm text-gray-70">{filteredArticles.length} articles</span>
                </div>

                {filteredArticles.map((article) => (
                  <div key={article.id} className="card p-6">
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-100">{article.title}</h3>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(article.difficulty)}`}>
                        {article.difficulty}
                      </span>
                    </div>

                    <p className="text-gray-70 mb-4">{article.content}</p>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 text-sm text-gray-60">
                        <span className="flex items-center space-x-1">
                          <ClockIcon className="w-3 h-3" />
                          <span>{article.readTime} min read</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <StarIcon className="w-3 h-3" />
                          <span>{article.helpful} helpful</span>
                        </span>
                        <span>Updated {article.lastUpdated.toLocaleDateString()}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="flex flex-wrap gap-1">
                          {article.tags.map((tag) => (
                            <span key={tag} className="px-2 py-1 bg-gray-20 text-xs text-gray-70 rounded">
                              {tag}
                            </span>
                          ))}
                        </div>
                        <button
                          onClick={() => markHelpful('article', article.id)}
                          className="btn-secondary text-sm"
                        >
                          Helpful
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* FAQs */}
            {activeSection === 'faqs' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-100">Frequently Asked Questions</h2>
                  <span className="text-sm text-gray-70">{filteredFAQs.length} questions</span>
                </div>

                {filteredFAQs.map((faq) => (
                  <div key={faq.id} className="card">
                    <button
                      onClick={() => setExpandedFAQ(expandedFAQ === faq.id ? null : faq.id)}
                      className="w-full p-6 text-left flex items-center justify-between hover:bg-gray-10"
                    >
                      <h3 className="font-medium text-gray-100">{faq.question}</h3>
                      {expandedFAQ === faq.id ? (
                        <ChevronDownIcon className="w-4 h-4 text-gray-60" />
                      ) : (
                        <ChevronRightIcon className="w-4 h-4 text-gray-60" />
                      )}
                    </button>

                    {expandedFAQ === faq.id && (
                      <div className="px-6 pb-6">
                        <p className="text-gray-70 mb-4">{faq.answer}</p>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-60 flex items-center space-x-1">
                            <StarIcon className="w-3 h-3" />
                            <span>{faq.helpful} people found this helpful</span>
                          </span>
                          <button
                            onClick={() => markHelpful('faq', faq.id)}
                            className="btn-secondary text-sm"
                          >
                            Helpful
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Videos */}
            {activeSection === 'videos' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-100">Video Tutorials</h2>
                  <span className="text-sm text-gray-70">{filteredVideos.length} videos</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredVideos.map((video) => (
                    <div key={video.id} className="card p-4">
                      <div className="relative mb-4">
                        <div className="w-full h-32 bg-gray-20 rounded-lg flex items-center justify-center">
                          <PlayIcon className="w-8 h-8 text-gray-60" />
                        </div>
                        <div className="absolute bottom-2 right-2 bg-gray-100 bg-opacity-80 px-2 py-1 rounded text-xs text-white">
                          {video.duration}
                        </div>
                      </div>

                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-medium text-gray-100">{video.title}</h3>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(video.difficulty)}`}>
                          {video.difficulty}
                        </span>
                      </div>

                      <p className="text-sm text-gray-70 mb-3">{video.description}</p>

                      <button className="btn-primary w-full">
                        Watch Tutorial
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Contact Support */}
            {activeSection === 'contact' && (
              <div className="space-y-6">
                <h2 className="text-xl font-semibold text-gray-100">Contact Support</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="card p-6">
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-10 h-10 bg-blue-10 rounded-full flex items-center justify-center">
                        <ChatBubbleLeftRightIcon className="w-5 h-5 text-blue-60" />
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-100">Live Chat</h3>
                        <p className="text-sm text-gray-70">Get instant help from our support team</p>
                      </div>
                    </div>
                    <button className="btn-primary w-full">Start Live Chat</button>
                  </div>

                  <div className="card p-6">
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-10 h-10 bg-green-10 rounded-full flex items-center justify-center">
                        <DocumentTextIcon className="w-5 h-5 text-green-60" />
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-100">Submit Ticket</h3>
                        <p className="text-sm text-gray-70">Create a support ticket for complex issues</p>
                      </div>
                    </div>
                    <button className="btn-secondary w-full">Create Ticket</button>
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">Quick Contact</h3>
                  <form className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Subject</label>
                      <input type="text" className="input-field w-full" placeholder="Brief description of your issue" />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Category</label>
                      <select className="input-field w-full">
                        <option>General Question</option>
                        <option>Technical Issue</option>
                        <option>Feature Request</option>
                        <option>Bug Report</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-100 mb-2">Message</label>
                      <textarea
                        className="input-field w-full h-32 resize-none"
                        placeholder="Describe your issue or question in detail..."
                      ></textarea>
                    </div>

                    <button type="submit" className="btn-primary">Send Message</button>
                  </form>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LightweightHelpCenter;
