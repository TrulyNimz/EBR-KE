import { BatchList } from '@/components/batch-records';

export const metadata = {
  title: 'Batch Records | EBR Platform',
  description: 'Manage batch records and production documentation',
};

export default function BatchRecordsPage() {
  return <BatchList />;
}
