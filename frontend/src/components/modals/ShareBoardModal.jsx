'use client';

import { useEffect, useMemo, useState } from 'react';
import { Copy, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { addBoardMember, getBoardMembers, removeBoardMember, updateBoardMember } from '../../lib/api/boards';
import { Button, Input, Modal, Select } from '../ui';

const ROLE_OPTIONS = [
  { value: 'viewer', label: 'Viewer' },
  { value: 'editor', label: 'Editor' },
  { value: 'admin', label: 'Admin' },
];

export default function ShareBoardModal({ isOpen, onClose, boardId, boardTitle }) {
  const [members, setMembers] = useState([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('viewer');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [updatingMemberId, setUpdatingMemberId] = useState(null);
  const [removingMemberId, setRemovingMemberId] = useState(null);

  const boardLink = useMemo(() => {
    if (!boardId || typeof window === 'undefined') {
      return '';
    }

    return `${window.location.origin}/dashboard/${boardId}`;
  }, [boardId]);

  const loadMembers = async () => {
    if (!boardId) return;

    setIsLoading(true);
    try {
      const data = await getBoardMembers(boardId);
      setMembers(data || []);
    } catch (error) {
      setMembers([]);
      toast.error(error.message || 'Failed to load board members');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    loadMembers();
  }, [isOpen, boardId]);

  const handleCopyLink = async () => {
    if (!boardLink) return;

    try {
      await navigator.clipboard.writeText(boardLink);
      toast.success('Board link copied');
    } catch {
      toast.error('Failed to copy board link');
    }
  };

  const handleAddMember = async (event) => {
    event.preventDefault();

    if (!email.trim()) {
      toast.error('Email is required');
      return;
    }

    setIsSubmitting(true);
    try {
      const createdMember = await addBoardMember(boardId, {
        email: email.trim(),
        role,
      });

      setMembers((prev) => [
        ...prev.filter((member) => String(member.user_id) !== String(createdMember.user_id)),
        createdMember,
      ]);
      setEmail('');
      setRole('viewer');
      toast.success('Board member added');
    } catch (error) {
      toast.error(error.message || 'Failed to add board member');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRoleChange = async (nextMemberId, nextRole) => {
    setUpdatingMemberId(nextMemberId);
    try {
      const updatedMember = await updateBoardMember(boardId, nextMemberId, { role: nextRole });
      setMembers((prev) => prev.map((member) => (
        String(member.user_id) === String(nextMemberId) ? updatedMember : member
      )));
      toast.success('Member role updated');
    } catch (error) {
      toast.error(error.message || 'Failed to update member role');
    } finally {
      setUpdatingMemberId(null);
    }
  };

  const handleRemoveMember = async (nextMemberId) => {
    setRemovingMemberId(nextMemberId);
    try {
      await removeBoardMember(boardId, nextMemberId);
      setMembers((prev) => prev.filter((member) => String(member.user_id) !== String(nextMemberId)));
      toast.success('Board member removed');
    } catch (error) {
      toast.error(error.message || 'Failed to remove board member');
    } finally {
      setRemovingMemberId(null);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Share Board"
      size="lg"
    >
      <div className="space-y-6">
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/40">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {boardTitle || 'Board access'}
          </p>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Copy the board link and manage board members below.
          </p>

          <div className="mt-3 flex flex-col gap-3 sm:flex-row">
            <input
              type="text"
              readOnly
              value={boardLink}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            />
            <Button type="button" variant="outline" onClick={handleCopyLink}>
              <Copy className="mr-2 h-4 w-4" />
              Copy Link
            </Button>
          </div>

          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Link sharing does not grant access by itself. Users still need to be added as board members.
          </p>
        </div>

        <form onSubmit={handleAddMember} className="space-y-4 rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="user@example.com"
            helperText="Enter the email of an existing registered user."
          />

          <Select
            label="Role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            options={ROLE_OPTIONS}
          />

          <div className="flex justify-end">
            <Button type="submit" loading={isSubmitting}>
              Add Member
            </Button>
          </div>
        </form>

        <div>
          <div className="mb-3 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              Members
            </h4>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {members.length}
            </span>
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">Loading members...</p>
          ) : members.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No board members found or you do not have permission to view them.
            </p>
          ) : (
            <div className="space-y-3">
              {members.map((member) => {
                const currentMemberId = String(member.user_id);

                return (
                  <div
                    key={currentMemberId}
                    className="flex flex-col gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
                        {member.name || member.email || currentMemberId}
                      </p>
                      <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                        {member.email || currentMemberId}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <Select
                        className="min-w-[120px]"
                        value={member.role}
                        onChange={(event) => handleRoleChange(currentMemberId, event.target.value)}
                        options={ROLE_OPTIONS}
                        disabled={updatingMemberId === currentMemberId}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveMember(currentMemberId)}
                        disabled={removingMemberId === currentMemberId}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
