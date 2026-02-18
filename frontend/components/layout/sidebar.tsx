'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  FileText,
  GitBranch,
  FormInput,
  Bell,
  Settings,
  Users,
  Shield,
  Activity,
  Hospital,
  Factory,
  Leaf,
  LogOut,
} from 'lucide-react';

const mainNavigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Batch Records', href: '/batch-records', icon: FileText },
  { name: 'Workflows', href: '/workflows', icon: GitBranch },
  { name: 'Forms', href: '/forms', icon: FormInput },
  { name: 'Notifications', href: '/notifications', icon: Bell },
];

const moduleNavigation = [
  { name: 'Healthcare', href: '/healthcare', icon: Hospital },
  { name: 'Manufacturing', href: '/manufacturing', icon: Factory },
  { name: 'Agriculture', href: '/agriculture', icon: Leaf },
];

const adminNavigation = [
  { name: 'Users', href: '/admin/users', icon: Users },
  { name: 'Roles', href: '/admin/roles', icon: Shield },
  { name: 'Audit Logs', href: '/admin/audit-logs', icon: Activity },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 hidden lg:block">
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="flex items-center h-16 px-6 border-b border-gray-200 dark:border-gray-700">
          <Link href="/dashboard" className="flex items-center">
            <span className="text-xl font-bold text-blue-600">EBR</span>
            <span className="text-xl font-semibold text-gray-900 dark:text-white ml-1">
              Platform
            </span>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Main Navigation */}
          <div>
            <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Main
            </h3>
            <div className="mt-2 space-y-1">
              {mainNavigation.map((item) => (
                <NavLink
                  key={item.name}
                  href={item.href}
                  icon={item.icon}
                  isActive={pathname.startsWith(item.href)}
                >
                  {item.name}
                </NavLink>
              ))}
            </div>
          </div>

          {/* Module Navigation */}
          <div>
            <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Modules
            </h3>
            <div className="mt-2 space-y-1">
              {moduleNavigation.map((item) => (
                <NavLink
                  key={item.name}
                  href={item.href}
                  icon={item.icon}
                  isActive={pathname.startsWith(item.href)}
                >
                  {item.name}
                </NavLink>
              ))}
            </div>
          </div>

          {/* Admin Navigation */}
          <div>
            <h3 className="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Administration
            </h3>
            <div className="mt-2 space-y-1">
              {adminNavigation.map((item) => (
                <NavLink
                  key={item.name}
                  href={item.href}
                  icon={item.icon}
                  isActive={pathname.startsWith(item.href)}
                >
                  {item.name}
                </NavLink>
              ))}
            </div>
          </div>
        </nav>

        {/* User Section */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button className="flex items-center w-full px-3 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <LogOut className="w-5 h-5 mr-3" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </aside>
  );
}

function NavLink({
  href,
  icon: Icon,
  isActive,
  children,
}: {
  href: string;
  icon: React.ElementType;
  isActive: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`flex items-center px-3 py-2 rounded-lg transition-colors ${
        isActive
          ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
      }`}
    >
      <Icon className="w-5 h-5 mr-3" />
      <span className="text-sm font-medium">{children}</span>
    </Link>
  );
}
