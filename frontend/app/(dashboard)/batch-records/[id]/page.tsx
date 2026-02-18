import { BatchDetail } from '@/components/batch-records';

interface BatchDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export async function generateMetadata({ params }: BatchDetailPageProps) {
  const resolvedParams = await params;
  return {
    title: `Batch ${resolvedParams.id} | EBR Platform`,
    description: 'View and manage batch record details',
  };
}

export default async function BatchDetailPage({ params }: BatchDetailPageProps) {
  const resolvedParams = await params;
  return <BatchDetail batchId={resolvedParams.id} />;
}
