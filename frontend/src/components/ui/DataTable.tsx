import { type ReactNode, useState, useMemo } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Inbox } from 'lucide-react';
import { Pagination } from './Pagination';

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T, index: number) => ReactNode;
  className?: string;
  align?: 'left' | 'right' | 'center';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
  emptyIcon?: LucideIcon;
  emptyTitle?: string;
  emptyDescription?: string;
  rowKey?: (row: T, index: number) => string | number;
  dense?: boolean;
}

const alignClasses = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
};

export function DataTable<T>({
  columns,
  data,
  pageSize = 10,
  emptyIcon = Inbox,
  emptyTitle = 'Nenhum registro encontrado',
  emptyDescription,
  rowKey,
  dense = false,
}: DataTableProps<T>) {
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.ceil(data.length / pageSize);
  const pageData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return data.slice(start, start + pageSize);
  }, [data, currentPage, pageSize]);

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
        <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
          {(() => {
            const Icon = emptyIcon;
            return <Icon className="w-6 h-6 text-slate-400" />;
          })()}
        </div>
        <h3 className="text-sm font-semibold text-slate-700">{emptyTitle}</h3>
        {emptyDescription && <p className="text-sm text-slate-500 mt-1 max-w-sm">{emptyDescription}</p>}
      </div>
    );
  }

  const cellPadding = dense ? 'px-3 py-2' : 'px-4 py-3';

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`${cellPadding} text-xs font-semibold text-slate-600 uppercase tracking-wider ${alignClasses[col.align || 'left']}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {pageData.map((row, idx) => {
              const absoluteIdx = (currentPage - 1) * pageSize + idx;
              return (
                <tr key={rowKey ? rowKey(row, absoluteIdx) : absoluteIdx} className="hover:bg-slate-50">
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`${cellPadding} text-sm text-slate-700 ${alignClasses[col.align || 'left']} ${col.className || ''}`}
                    >
                      {col.render(row, absoluteIdx)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={setCurrentPage}
        totalItems={data.length}
        itemsPerPage={pageSize}
      />
    </div>
  );
}
