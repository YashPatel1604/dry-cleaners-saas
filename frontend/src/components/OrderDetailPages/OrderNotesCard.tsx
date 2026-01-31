import { useState } from 'react';
import { Card } from '../ui/card';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';

interface OrderNotesCardProps {
  notes?: string;
  onAddNote?: (note: string) => void;
}

export function OrderNotesCard({ notes, onAddNote }: OrderNotesCardProps) {
  const [noteText, setNoteText] = useState('');

  const handleAddNote = () => {
    if (noteText.trim() && onAddNote) {
      onAddNote(noteText);
      setNoteText('');
    }
  };

  return (
    <Card className="p-6">
      <h2 className="text-xl text-gray-800 mb-4">Notes</h2>
      
      {notes && (
        <div className="mb-4 p-3 bg-gray-50 rounded-lg">
          <p className="text-gray-900 whitespace-pre-wrap">{notes}</p>
        </div>
      )}

      <div className="space-y-3">
        <Textarea
          placeholder="Add internal notes"
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          rows={4}
        />
        <Button onClick={handleAddNote} disabled={!noteText.trim()}>
          Add Note
        </Button>
      </div>
    </Card>
  );
}
