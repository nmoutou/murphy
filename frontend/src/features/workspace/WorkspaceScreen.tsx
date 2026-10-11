import Workspace from './Workspace';
import WorkspaceHeader from './WorkspaceHeader';

export default function WorkspaceScreen() {
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-primary">
      <WorkspaceHeader />
      <Workspace />
    </div>
  );
}
