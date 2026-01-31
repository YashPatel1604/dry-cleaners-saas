import { Card } from '../ui/card';
import { Button } from '../ui/button';

interface CustomerNotesCardProps {
  popUpMessage?: string;
  onEdit?: () => void;
}

export function CustomerNotesCard({ popUpMessage, onEdit }: CustomerNotesCardProps) {
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl text-gray-800">Pop-up Message</h2>
        {onEdit && (
          <Button variant="outline" size="sm" onClick={onEdit}>
            Edit
          </Button>
        )}
      </div>
      
      {popUpMessage ? (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-gray-900 whitespace-pre-wrap">{popUpMessage}</p>
        </div>
      ) : (
        <p className="text-gray-600 italic">No pop-up message</p>
      )}
    </Card>
  );
}
