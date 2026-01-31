interface TopNavProps {
  activeSection: string;
  setActiveSection: (section: string) => void;
}

export function TopNav({ activeSection, setActiveSection }: TopNavProps) {
  return (
    <nav className="bg-white border-b border-gray-200 px-8 py-4">
      <div className="flex items-center justify-between max-w-7xl">
        <button
          onClick={() => setActiveSection('drop')}
          className={`px-6 py-2 rounded transition-colors ${
            activeSection === 'drop'
              ? 'bg-blue-600 text-white'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          DROP
        </button>
        <button
          onClick={() => setActiveSection('home')}
          className={`px-6 py-2 rounded transition-colors ${
            activeSection === 'home'
              ? 'bg-blue-600 text-white'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          HOME
        </button>
        <button
          onClick={() => setActiveSection('dashboard')}
          className={`px-6 py-2 rounded transition-colors ${
            activeSection === 'dashboard'
              ? 'bg-blue-600 text-white'
              : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          DASHBOARD
        </button>
      </div>
    </nav>
  );
}
